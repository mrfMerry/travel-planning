#!/usr/bin/env python3
"""Serialize Xiaohongshu MCP tools/call requests to one call every 30 seconds."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import time
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit


INTERVAL_SECONDS = 30.0
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}
SKIP_REQUEST_HEADERS = HOP_BY_HOP | {"host", "content-length", "accept-encoding"}


def plan_slot(last_started_at: float | None, now: float, interval: float = INTERVAL_SECONDS) -> float:
    """Return the earliest timestamp at which the next tools/call may start."""
    if last_started_at is None:
        return now
    return max(now, last_started_at + interval)


def is_tools_call(body: bytes) -> bool:
    if not body:
        return False
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    messages = payload if isinstance(payload, list) else [payload]
    return any(isinstance(item, dict) and item.get("method") == "tools/call" for item in messages)


def reserve_tools_call(state_path: Path, interval: float = INTERVAL_SECONDS) -> float:
    """Block until this tools/call is allowed, then record its start time."""
    state_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with state_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.seek(0)
            raw = handle.read().strip()
            last_started_at = None
            if raw:
                try:
                    last_started_at = float(json.loads(raw)["last_started_at"])
                except (TypeError, ValueError, KeyError, json.JSONDecodeError):
                    last_started_at = None
            now = time.time()
            start_at = plan_slot(last_started_at, now, interval)
            waited = start_at - now
            handle.seek(0)
            handle.truncate()
            handle.write(json.dumps({"last_started_at": start_at}))
            handle.flush()
            os.fsync(handle.fileno())
            try:
                state_path.chmod(0o600)
            except OSError:
                pass
            if waited > 0:
                time.sleep(waited)
            return waited
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _copy_headers(source: Iterable[tuple[str, str]], skipped: set[str]) -> dict[str, str]:
    copied = {}
    for key, value in source:
        if key.lower() not in skipped:
            copied[key] = value
    return copied


class RateLimitProxy(BaseHTTPRequestHandler):
    upstream_host = "127.0.0.1"
    upstream_port = 18061
    state_path = Path.home() / ".local" / "share" / "travel-planning" / "xiaohongshu-mcp" / "state" / "rate-limit.json"
    interval_seconds = INTERVAL_SECONDS
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802
        self._handle()

    def do_POST(self) -> None:  # noqa: N802
        self._handle()

    def do_DELETE(self) -> None:  # noqa: N802
        self._handle()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._handle()

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("%s - %s\n" % (self.log_date_time_string(), fmt % args))

    def _handle(self) -> None:
        if self.command == "GET" and urlsplit(self.path).path == "/travel-planning-rate-limit":
            self._write_json(self._status_payload())
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else b""
        if is_tools_call(body):
            reserve_tools_call(self.state_path, self.interval_seconds)
        self._forward(body)

    def _status_payload(self) -> dict[str, object]:
        last_started_at = None
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            last_started_at = float(payload["last_started_at"])
        except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError):
            last_started_at = None
        remaining = 0.0
        if last_started_at is not None:
            remaining = max(0.0, last_started_at + self.interval_seconds - time.time())
        return {
            "enabled": True,
            "interval_seconds": self.interval_seconds,
            "next_tools_call_in_seconds": round(remaining, 3),
        }

    def _write_json(self, payload: dict[str, object]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(encoded)

    def _forward(self, body: bytes) -> None:
        connection = HTTPConnection(self.upstream_host, self.upstream_port, timeout=300)
        try:
            headers = _copy_headers(self.headers.items(), SKIP_REQUEST_HEADERS)
            if body:
                headers["Content-Length"] = str(len(body))
            connection.request(self.command, self.path, body=body or None, headers=headers)
            upstream = connection.getresponse()
            payload = upstream.read()
            self.send_response(upstream.status)
            for key, value in _copy_headers(upstream.getheaders(), HOP_BY_HOP).items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(payload)
        except OSError as error:
            message = json.dumps({"error": f"小红书上游不可用：{error}"}).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(message)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(message)
        finally:
            connection.close()


def serve(listen_host: str, listen_port: int, upstream: str, state_path: Path) -> None:
    parsed = urlsplit(upstream)
    if parsed.scheme != "http" or not parsed.hostname or parsed.port is None:
        raise SystemExit("upstream 必须是带端口的 http:// 地址")
    RateLimitProxy.upstream_host = parsed.hostname
    RateLimitProxy.upstream_port = parsed.port
    RateLimitProxy.state_path = state_path
    server = ThreadingHTTPServer((listen_host, listen_port), RateLimitProxy)
    server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listen", default="127.0.0.1:18060")
    parser.add_argument("--upstream", default="http://127.0.0.1:18061")
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    host, separator, port = args.listen.rpartition(":")
    if not separator or host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("--listen 只能绑定本机 loopback")
    serve(host, int(port), args.upstream, args.state.expanduser().resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
