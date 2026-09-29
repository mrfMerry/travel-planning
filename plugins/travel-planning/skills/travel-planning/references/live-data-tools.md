# 实时数据工具

除“小红书路线前轻量预研”外，只在路线已确认并进入深度规划时读取。这里说明跨来源预检、标准快照落盘和本 Skill 自带的适配命令；供应商工具参数、安装与登录遵循 `/flyai`、`/variflight`、`/amap-maps` 和 `/xiaohongshu`。

## 小红书路线前轻量预研

在给出 2～3 个路线方案前，若小红书服务已配置并处于可用登录态，执行一次有上限的只读扫描：

1. 查询目的地与行程长度的组合，例如“兰州 一日游”；再查询目的地与“必吃/美食”的组合；只有季节会改变体验时再增加月份或季节查询。
2. 每类查询只挑选少量高相关原帖读取详情，优先覆盖不同作者、不同发布时间和不同路线取舍，不按互动数机械取前几名。
3. 提取反复出现的景点组合、推荐时段、排队与绕行风险、地方菜品或美食类别；同时记录冲突、疑似推广和样本不足。
4. 输出 `route-context.json`，供路线方案和后续餐厅研究读取。这里的美食内容是“目的地美食主题”，不是具体门店推荐，也不能证明某家店有售、营业或值得专程绕行。

若服务未启动、未登录、触发验证或查询失败，记录状态和建议查询词后继续生成路线方案；路线确认阶段不得因此启动安装、扫码登录、反复重试或改用搜索摘要冒充原帖。

## 前置健康检查

```bash
python3 skills/travel-planning/scripts/research_sources.py preflight \
  --city "杭州" \
  --airport HGH \
  --require amap-maps \
  --require flyai \
  --require open-meteo \
  --require xiaohongshu
```

`preflight` 对插件 MCP 执行 `initialize`、`tools/list`、工具契约检查和只读上游探测，并验证飞猪、天气与小红书的真实运行态。状态使用 `ready`、`degraded` 或 `unavailable`；只有本次 `--require` 的来源未就绪时返回非零。`--skip-upstream` 只用于离线诊断，不能作为开始深度研究的依据。

可要求的来源为 `amap-maps`、`variflight-aviation`、`variflight-tripmatch`、`flyai`、`open-meteo` 和 `xiaohongshu`。只有涉及航班时要求 Aviation，铁路或空铁联运要求 Tripmatch，中国境内地图要求高德。`capabilities` 只表示适配器和配置存在，不表示实时健康。

## 查询与落盘边界

- 路线确认后的已配置只读查询可直接执行，不逐次请求同意；不得扩展到预订、占座、付款、发布、互动或订单修改。
- 正式研究命令同时传入 `--workspace` 和 `--task-id`。航班、铁路和空铁联运属于 `route-data`，酒店属于 `stay-food`。
- 飞猪和飞常准响应由 `scripts/source_adapters.py` 转换为 `travel-source-snapshot/v1`，遵守 `schemas/travel-source-snapshot.schema.json`。错误遵守 `schemas/travel-source-error.schema.json`。
- 标准快照写入 `snapshots/<task_id>/`；研究结果只提交 `source_snapshot_ids[]`。采用的交通或住宿候选通过 `inventory_refs[]` 绑定具体 `snapshot_id + offer_id`。
- 原始供应商私有字段、凭证、Cookie、授权头和临时令牌不得进入 workspace 或行程。

## 航班、铁路与住宿

通用发现先使用 `/flyai`，运行状态、指定航班、铁路和空铁联运补充使用 `/variflight`。开放式航班和铁路候选必须覆盖最早、最晚、时长、价格和推荐排序，不能用单次低价榜推断全天没有合适班次。

需要写入标准快照时使用包装命令：

```bash
python3 skills/travel-planning/scripts/research_sources.py flyai-flight-coverage \
  --origin "北京" --destination "上海" --date 2026-10-03 \
  --workspace ".travel-research/example-trip" --task-id route-data

python3 skills/travel-planning/scripts/research_sources.py flyai-train-coverage \
  --origin "北京南" --destination "上海虹桥" --date 2026-10-03 \
  --workspace ".travel-research/example-trip" --task-id route-data

python3 skills/travel-planning/scripts/research_sources.py flyai-hotel \
  --destination "杭州" --poi "西湖" \
  --check-in 2026-10-03 --check-out 2026-10-05 \
  --adults 4 --rooms 2 --bed-type "双床房" \
  --workspace ".travel-research/example-trip" --task-id stay-food
```

商圈酒店查询只用于发现。采用前以酒店全名再次查询，并用地图核对城市、行政区、地址、坐标和目标锚点。供应商没有按多间同房型校验库存时，只能标为报价候选。

飞常准包装命令包括 `variflight-flight`、`variflight-flight-number`、`variflight-flight-price`、`variflight-flight-comfort`、`variflight-train`、`variflight-train-stations` 和 `variflight-air-rail`。IATA 参数使用三位城市或机场代码；价格和空铁联运只接受城市代码。缺凭证、授权失败、额度不足、空结果和供应商故障必须分别保留，不能统一改写成“没有班次”。

## 天气、地图与境外地点

近期天气使用 Open-Meteo；中国天气预警另保留官方预警入口：

```bash
python3 skills/travel-planning/scripts/research_sources.py weather \
  --location "杭州" --days 7
```

中国境内 POI 与路线遵循 `/amap-maps`。需要包装输出时使用：

```bash
python3 skills/travel-planning/scripts/research_sources.py amap-place \
  --city "杭州" --keywords "西湖风景区 曲院风荷入口"

python3 skills/travel-planning/scripts/research_sources.py amap-route \
  --origin "120.130210,30.259002" \
  --destination "120.144590,30.243710" \
  --mode walking
```

高德返回的路线耗时不等于门到门时间；还要加入出入口步行、等待、换乘、安检和缓冲。入口开放状态回到景区官方确认。

境外地点可用 Nominatim/OpenStreetMap 低频发现坐标候选：

```bash
python3 skills/travel-planning/scripts/research_sources.py osm-place \
  --query "Kiyomizu-dera Niomon, Kyoto, Japan" \
  --countrycodes jp --limit 3
```

一次只发一个请求，不并发扫点或批量抓取。返回坐标只是候选，入口名称与开放状态仍需官方和实际地图平台确认；同一组路线不得混用 GCJ-02 与 WGS84。

## 小红书体验研究

搜索、详情、登录和工具参数遵循 `/xiaohongshu`。旅行研究默认只读；使用本 Skill 的 `xhs-search` 或 `xhs-detail` 包装输出时，临时令牌只保存在权限受限的用户缓存，workspace 只保存公开原帖链接、必要摘要和查询时间。研究方法与证据边界见[信息获取与核验策略](source-strategy.md)。

路线确认后的具体景点和餐厅研究可以复用 `route-context.json` 的查询词与地方美食主题，但必须重新核验具体实体、适用日期、地图位置和经营信息；不得把路线前样本数算作某家餐厅的门店口碑样本。

## 手动查询降级

自动获取失败或不允许自动化时，使用 `fallback` 生成带查询条件的 `action_links[]`：

```bash
python3 skills/travel-planning/scripts/research_sources.py fallback --kind train \
  --origin "北京南" --destination "上海虹桥" --date "2026-10-03" \
  --fields "车次、时刻、二等座票价和余票"

python3 skills/travel-planning/scripts/research_sources.py fallback --kind ctrip \
  --product "酒店" --city "杭州" --date "2026-10-03 至 2026-10-05" \
  --travelers "2 位成人·1 间房"

python3 skills/travel-planning/scripts/research_sources.py fallback --kind map \
  --city "杭州" --keywords "西湖风景区 曲院风荷入口"

python3 skills/travel-planning/scripts/research_sources.py fallback --kind xiaohongshu \
  --keywords "西湖 10月 日落 入口 避坑"
```

景区 fallback 必须传入已经核对的官方 URL。手动入口只表示待复核，不能把平台首页或查询页写成已核验详情。

## 合并规则

- 主 Agent 将标准快照合并到 `planning.source_snapshots[]`；页面展示 Provider、查询时间、有效期和供应商实际返回的 HTTPS 入口。
- 动态报价、库存、时刻、运行状态和地图耗时只属于本次 workspace。机场、车站、酒店身份等跨 Agent 需要的字段写入本次 `shared_entities[]`，不建立跨行程缓存。
- 高德和天气结果使用 `platform_reported`，人工查询入口使用 `to_recheck`。
