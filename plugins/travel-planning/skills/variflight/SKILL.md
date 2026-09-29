---
name: variflight
description: 使用插件已配置的飞常准 Aviation 与 Tripmatch MCP 查询航班班次、运行状态、价格、舒适度、机场天气、火车和空铁联运候选。适用于航班号核验、城市或机场间交通查询及铁路候选，在 Grok 中使用 /variflight；不用于代订、出票或替代航司和 12306 的最终确认。
---

# 飞常准 MCP

一个 Skill 统一引导两个 MCP Server：

- `variflight-aviation`：航班搜索、指定航班状态、价格、舒适度、实时位置和机场天气。
- `variflight-tripmatch`：火车、空铁联运，以及需要跨交通方式比较的场景。

航班单项查询优先 Aviation；只有火车或空铁联运才优先 Tripmatch，避免对两个 Server 重复发相同查询。

## 查询路由

- 城市/机场间直飞：`searchFlightsByDepArr`。
- 已知航班号：`searchFlightsByNumber`；舒适度、准点率、机型和餐食使用 `flightHappinessIndex`。
- 城市间结构化价格：`getFlightPriceByCities`；自然语言推荐摘要使用 `searchFlightItineraries`。
- 已知飞机注册号的实时位置：`getRealtimeLocationByAnum`；不知道注册号时不要猜。
- 机场三日天气：`getFutureWeatherByAirport`。
- 城市级铁路覆盖：Tripmatch 的 `searchTrainTicketsByCity`；明确到具体车站时用 `searchTrainTicketsByStation`。不要调用已弃用的 `searchTrainTickets`。
- 车站名不确定时先用 `searchTrainStations`；空铁联运使用 `getFlightAndTrainTransferInfo`。

调用前按需读取[工具选择与参数约束](references/tool-routing.md)。

## 约束

- 日期使用完整 `YYYY-MM-DD`。相对日期先结合当前时区解析；需要供应商侧“今天”时调用 `getTodayDate`，不得把示例日期当成当前日期。
- 城市 IATA 码和机场 IATA 码不可混用：城市用 `depcity/arrcity`，具体机场用 `dep/arr`；每一端只选一种。价格和空铁联运工具要求城市码。
- 火车城市查询和具体车站查询语义不同。用户指定“北京南”“上海虹桥”时保留站级条件，不得擅自扩大为全城。
- 价格、余量、班次、运行状态和天气均为查询时快照。中国铁路最终回到 12306，航班关键状态最终回到航司或机场；不得把候选描述成已出票或已预订。
- 不输出、记录或传递 `VARIFLIGHT_API_KEY`，不执行订单、占座、付款或乘客信息提交。

完整旅行规划中，需要持久化或采用某个候选时，交给 `/travel-planning` 的标准快照适配器写入 `travel-source-snapshot/v1`；本 Skill 的原始 MCP 返回不能直接成为行程层契约。在 Grok 中用 `search_tool` 与 `use_tool` 调用 `variflight-aviation`、`variflight-tripmatch` 的 MCP 工具。
