---
name: flyai
description: 使用插件内锁定版本的飞猪 FlyAI 通用能力搜索航班、火车、酒店、景点、活动和旅行产品。适用于需要飞猪实时平台候选或比价的旅行任务，在 Grok 中使用 /flyai；只读搜索可直接执行，预订和付款必须交给用户确认并在外部平台完成。
---

# 飞猪 FlyAI

本 Skill 直接集成 `alibaba-flyai/flyai-skill` 的通用检索流程，通过固定版本 `@fly-ai/flyai-cli@1.0.16` 访问飞猪 MCP API，不在插件内重复实现供应商协议。

## 执行入口

在插件根目录运行：

```bash
python3 scripts/providers/flyai_cli.py <command> [arguments]
```

上游文档中的 `flyai ...` 命令均映射到上述插件级包装入口。统一环境加载器优先读取插件根目录的 `config/sources.local.env`，安装包中没有该文件时回退到用户级 `~/.config/travel-planning/sources.local.env`，并兼容旧配置目录；它只向 FlyAI 子进程传递自己的配置，不会输出或写回凭证。

## 能力路由

调用前读取对应参数文档，不猜测参数：

- 通用关键词发现：[`references/keyword-search.md`](references/keyword-search.md)
- 自然语言语义检索：[`references/ai-search.md`](references/ai-search.md)
- 航班：[`references/search-flight.md`](references/search-flight.md)
- 火车：[`references/search-train.md`](references/search-train.md)
- 酒店：[`references/search-hotel.md`](references/search-hotel.md)
- 景点与门票：[`references/search-poi.md`](references/search-poi.md)
- 万豪酒店与套餐：[`references/search-marriott-hotel.md`](references/search-marriott-hotel.md)和[`references/search-marriott-package.md`](references/search-marriott-package.md)

## 边界

- 搜索、比较和获取公开跳转链接属于只读操作，可以在路线确认后的研究阶段直接执行。
- 返回的价格、库存和班次是查询时的平台快照；下单前必须重新核验。
- “预订”链接只用于把用户交给飞猪页面。不得代替用户提交订单、占座、付款、填写乘客或入住人信息。
- 供应商原始结果进入旅行规划时，使用 `travel-planning` 的标准快照适配器；不得把凭证或供应商私有字段写入行程。

上游来源、固定 revision 与许可见 [`references/upstream.lock.json`](references/upstream.lock.json) 和 [`references/NOTICE.md`](references/NOTICE.md)。
