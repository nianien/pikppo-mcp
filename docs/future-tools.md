# pikppo-mcp 未来工具候选

记录后续可能引入的外部工具。**纳入前先过边界**（见 `technical-design.md` §1）：只有真正的外部操作（访问第三方系统 / 跨用户共享 / 需服务端算力或密钥）才进本服务；个人领域数据（日历、笔记、待办、联系人…）归客户端本地存储，不做成服务端工具。

每项标注：**归属**（是否属 pikppo-mcp）、**数据源候选**（优先免费免 key，与 exchange 现有风格一致）、**是否落库**、**设计要点**。已实现的 exchange 见 `technical-design.md` §8。

> 优先级仅为相对排序参考，未承诺排期。

## 一、明确属于 pikppo-mcp（外部操作）

### 🌐 翻译（translate）
- **归属**：✅ 外部操作（调第三方翻译引擎）
- **工具草案**：`translate_text`（text / source? / target）、`detect_language`（text）
- **数据源候选**：DeepL Free（500k 字/月，需 key）、LibreTranslate（可自建/公共实例，免 key）、Google Cloud Translation（需 key + 计费）
- **落库**：否，只读直连
- **设计要点**：source 缺省时先 detect；引擎差异封装在 service 层，工具契约稳定；长文本分段与字数限额留意

### ☀️ 天气（weather）
- **归属**：✅ 外部操作
- **工具草案**：`get_current_weather`（location）、`get_forecast`（location / days）
- **数据源候选**：Open-Meteo（**免费免 key**，含预报，首选，最贴合 exchange 模式）、OpenWeatherMap（需 key）
- **落库**：否；可进程内 TTL 缓存（同 exchange，按数据源更新粒度缓存）
- **设计要点**：location 支持城市名需先地理编码（Open-Meteo 自带 geocoding API）；时区/单位（℃/℉、风速）作为参数

### 🔍 联网搜索（web_search）
- **归属**：✅ 外部操作（需服务端密钥/算力）
- **工具草案**：`web_search`（query / count?）、可选 `fetch_url`（url，抓正文）
- **数据源候选**：Brave Search API（需 key，有免费档）、Tavily（面向 LLM，需 key）、SearXNG（可自建，免 key）
- **落库**：否
- **设计要点**：密钥走 Secret Manager（同 MCP_AUTH_TOKEN）；结果做摘要/截断控制 token；`fetch_url` 注意 SSRF 防护（限制内网地址）

### 🗺️ 地图导航（maps）
- **归属**：✅ 外部操作
- **工具草案**：`geocode`（address）、`search_places`（query / near?）、`get_directions`（origin / destination / mode?）
- **数据源候选**：OpenStreetMap Nominatim（geocode，免 key，有调用频率礼仪限制）+ OSRM/OpenRouteService（路线，ORS 需 key 免费档）、高德/Google（需 key + 计费）
- **落库**：否
- **设计要点**：国内场景考虑高德（坐标系 GCJ-02 与 WGS-84 转换）；遵守各源的 rate limit 与署名要求

### 📧 邮件（email）
- **归属**：✅ 外部操作（操作第三方邮箱服务），但**是写操作 + 强敏感**，单列权衡
- **工具草案**：`list_emails` / `get_email` / `summarize_inbox` / `send_email` / `draft_reply`
- **数据源候选**：Gmail API（OAuth2）、IMAP/SMTP（通用）、Microsoft Graph（Outlook）
- **落库**：可能需要——OAuth token / 刷新令牌按用户持久化（属「第三方集成状态」，符合落库边界）→ 这会是**第一个真正给 storage 框架挂表的工具**
- **设计要点**：
  - OAuth 授权流不在 MCP 内做（客户端完成），服务端只存/用 token；token 加密存储
  - `send_email` 是不可逆外部副作用，按写操作谨慎设计（确认/草稿优先）
  - 多用户隔离：此处才真正需要 `user_id` 维度（见 technical-design §9「确定做多用户时再加」）

### 📈 股票 / 基金查询与分析（stock_fund）
- **归属**：✅ 外部操作（调第三方行情数据源）
- **数据源候选**：
  - A 股/港股/基金：AkShare（Python 库，聚合东财/新浪/腾讯等多源，**免 key**，与本项目 Python 栈天然契合，首选）、天天基金（fund.eastmoney.com，非官方接口）、新浪/腾讯行情接口（免 key，非官方）
  - 美股：Alpha Vantage / Finnhub（免费档需 key，有频率限制）、Yahoo Finance（非官方）
- **落库**：否；历史序列可进程内 TTL 缓存（同 exchange）

**可查数据范围**（落地以具体源为准，覆盖度 A 股 + 场内基金最全，美股次之，港股偏弱）：

| 类别 | 股票 | 基金 |
|------|------|------|
| 行情 | 实时快照（最新价/涨跌幅/开高低收/成交量额/换手率）、历史 K 线（日周月 + 分钟级，前/后复权）、买卖五档 | 单位/累计净值、日增长率、历史净值序列；场内 ETF/LOF 实时行情 + 盘中估值 |
| 基本面/配置 | 估值（PE/PB/PS/股息率/市值）、三大报表、财务指标（营收净利及增速/ROE/毛利率/负债率/EPS）、分红送配 | 资产配置、重仓股、行业分布（季报，有滞后） |
| 业绩/风险 | 区间涨跌幅、最高/最低、最大回撤（service 层算） | 近 1 月/3 月/1 年/成立来收益、同类排名、最大回撤、夏普 |
| 资金/交易 | 资金流向（主力/大/中/小单）、北向持股、融资融券、龙虎榜、股东户数 | 规模与份额变化、申赎情况 |
| 公司/事件 | 简介、行业、概念板块、公告、业绩预告、解禁、停复牌 | 基金类型、经理（任职年限/业绩）、基金公司、费率 |
| 板块/大盘 | 行业/概念板块行情与资金流、指数行情与成分权重、涨跌停/涨跌家数 | — |

**工具草案**（字段对 LLM 统一；symbol/代码规范化收在 service 层）：
- `get_stock_quote(symbol)` → 实时快照：价/涨跌幅/开高低收/成交量额/换手率/PE/PB/市值/五档
- `get_stock_history(symbol, start, end, period=daily, adjust=qfq)` → K 线序列 + 基础统计（区间涨跌幅、最高/最低、均线、最大回撤）
- `get_stock_fundamentals(symbol)` → 估值 + 关键财务指标 + 分红历史
- `get_stock_capital_flow(symbol)`（进阶）→ 资金流向、北向持股、融资融券
- `get_fund_nav(code, start?, end?)` → 最新净值；带区间时返回净值序列 + 区间收益统计
- `get_fund_profile(code)` → 类型/规模/经理/费率 + 多周期收益与同类排名、最大回撤
- `get_fund_holdings(code)`（进阶）→ 重仓股、资产配置、行业分布（季报）
- 可选：`get_index_quote(symbol)`、`get_sector_ranking(kind)`（板块/指数维度）

- **设计要点**：
  - **工具只提供数据 + 基础统计，分析与买卖建议交给 LLM**（仿 `get_exchange_trend` 的 service 层统计），工具不下结论
  - **合规**：免费/非官方源多为延迟行情（~15min），财务/持仓按报告期有滞后；输出需带「不构成投资建议」免责语义
  - 分阶段：先打通 A 股行情（`get_stock_quote` + `get_stock_history`）与基金净值，再加基本面/资金流等进阶工具

### 🛒 电商 / 本地生活 搜索与 AI 推荐（ecommerce）
> 现阶段为想法。接入路线已定：**走各平台官方申请备案 / 正式授权**（联盟或开放平台），不做爬虫。

- **归属**：✅ 外部操作（搜索第三方电商/本地生活平台），LLM 基于查询结果做综合分析与推荐
- **覆盖设想**：美团（本地生活/餐饮）、淘宝/天猫、京东、拼多多、阿里——搜索商品/服务
- **典型场景（对话驱动推荐）**：用户问「今天吃什么」→ LLM 结合上下文（位置、口味、预算、历史）→ 调 `search_*` 查餐饮/商品 → 对返回结果（评分、价格、距离、评价）做综合分析 → 给出推荐。即 **工具负责「查」，LLM 负责「analysis + 推荐」**，与股票/汇率工具同一分工。
- **工具草案**：`search_products`（platform / query / filters?）、`search_local_life`（如美团：品类 / 位置 / 价位）、`get_detail`（platform / id）
- **接入路线（官方授权）**：
  - 淘宝/天猫 → 阿里妈妈淘宝客（TBK）；京东 → 京东联盟（union.jd.com）；拼多多 → 多多进宝；美团 → 美团联盟 / 开放平台
  - 均需注册主体 + 申请 app key/secret + 审核备案；受各平台 ToS 与内容合规约束
  - 注意：联盟接口自带「返利/带货」属性，结果偏导购而非中立，产品层需权衡如何呈现
- **落库**：可能需要——平台 app 凭证 / 用户授权 token 按用户持久化（属第三方集成状态，符合落库边界），同邮件
- **设计要点**：
  - 各平台 API 形态差异大（鉴权、签名、字段），由 service 层适配，工具契约对 LLM 统一
  - **分平台分阶段**落地，先打通一家（如美团本地生活满足「今天吃什么」场景，或京东联盟文档相对开放）验证链路，再横向扩展
  - 推荐所需的个性化上下文（口味偏好、历史）属**个人数据，由客户端按需提供给 LLM**，不在本服务存储（见 §1 边界）
  - 签名密钥走 Secret Manager；遵守各平台频率与内容合规要求

## 二、按边界归客户端本地（不做成服务端工具）

### ✅ 待办清单 / 笔记 / 联系人（todo / notes / contacts）
- **归属**：❌ **个人领域数据 → 客户端本地存储**，不进 pikppo-mcp
- **理由**：真相源在本地个人数据存储，跨设备同步由该存储层统一负责，不为每个领域在服务端开 CRUD（见 [local-first 边界]，technical-design §1）
- **保留的价值**：「LLM 从对话创建待办」仍成立，但 LLM 调的是**客户端写本地存储**的接口，不是 MCP 工具
- **例外**：若要接入**第三方**待办服务（如 Todoist / Google Tasks）做双向同步，那属于外部操作，可作为独立工具进 MCP——与「本地待办」是两回事

### 🗓️ 第三方日历同步（external_calendar，可选）
- **归属**：⚠️ 视形态而定。本地日历已归客户端；但接入 **Google Calendar / CalDAV** 等第三方日历做读写，属外部操作，可作为新工具
- **与已撤出的 calendar 区分**：撤掉的是「服务端自建日历表 + CRUD」；这里是「桥接外部日历服务」，归属不同
- **落库**：同邮件，OAuth token 可能需持久化

## 三、纳入新工具的落地清单

1. 过边界（本文 §1 判断准则）→ 确认属外部操作
2. `tools/` + `services/` + （需落库时）`models/` 各加一个模块，复用现有认证/传输/部署基建
3. 工具用 `@mcp.tool(name=, title=, description=)` 三字段 + 参数 `Annotated[..., Field(description=...)]`（见 technical-design §4）
4. 需密钥的源走 Secret Manager + 最小权限 SA
5. 需服务端落库的，把表 DDL 追加到 `storage/postgres.py` 的 `SCHEMA` 并重跑 `scripts/init-db.py`（首次挂表即激活休眠的 DB 框架）
6. 测试：纯外部 API 工具 mock 数据源不依赖网络（同 `test_exchange.py`）；落库工具再恢复 `pikppo_test` 测试库方案
