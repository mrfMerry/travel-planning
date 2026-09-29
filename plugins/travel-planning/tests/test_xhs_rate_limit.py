from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "skills" / "xiaohongshu" / "scripts" / "xhs_rate_limit.py"
SPEC = importlib.util.spec_from_file_location("xhs_rate_limit", MODULE_PATH)
assert SPEC and SPEC.loader
xhs_rate_limit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(xhs_rate_limit)


class XhsRateLimitTest(unittest.TestCase):
    def test_slot_is_at_least_thirty_seconds_after_the_previous_start(self) -> None:
        self.assertEqual(xhs_rate_limit.plan_slot(None, 1000), 1000)
        self.assertEqual(xhs_rate_limit.plan_slot(1000, 1010), 1030)
        self.assertEqual(xhs_rate_limit.plan_slot(1000, 1030), 1030)
        self.assertEqual(xhs_rate_limit.plan_slot(1000, 1045), 1045)

    def test_only_tools_call_is_limited(self) -> None:
        self.assertTrue(xhs_rate_limit.is_tools_call(b'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{}}'))
        self.assertTrue(
            xhs_rate_limit.is_tools_call(
                b'[{"method":"initialize"},{"method":"tools/call","params":{}}]'
            )
        )
        self.assertFalse(xhs_rate_limit.is_tools_call(b'{"method":"tools/list","params":{}}'))
        self.assertFalse(xhs_rate_limit.is_tools_call(b'{"method":"initialize"}'))
        self.assertFalse(xhs_rate_limit.is_tools_call(b""))
        self.assertFalse(xhs_rate_limit.is_tools_call(b"not-json"))

    def test_reserve_persists_start_and_waits_out_the_remainder(self) -> None:
        sleeps: list[float] = []
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "rate-limit.json"
            with (
                patch.object(xhs_rate_limit.time, "time", side_effect=[100.0, 110.0]),
                patch.object(xhs_rate_limit.time, "sleep", side_effect=sleeps.append),
            ):
                self.assertEqual(xhs_rate_limit.reserve_tools_call(state), 0)
                self.assertEqual(xhs_rate_limit.reserve_tools_call(state), 20)
            saved = json.loads(state.read_text(encoding="utf-8"))
        self.assertEqual(sleeps, [20.0])
        self.assertEqual(saved["last_started_at"], 130.0)


if __name__ == "__main__":
    unittest.main()
