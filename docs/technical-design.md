# pikppo-mcp 技术方案

pikppo 的**外部工具** MCP 服务：通过 MCP 协议向 pikppo Flutter 客户端及任意 MCP 兼容客户端暴露可被 LLM 调用的外挂能力（日程、邮件、翻译、地图、天气……）。本文记录整体架构、关键选型与设计依据；面向开发的操作规范见 `CLAUDE.md`。

## 1. 定位与边界

服务只承载**外部工具**——LLM 该主动调用、用于操作真实世界服务的能力。app 自身的内在能力（记忆、角色、群组、用户设置、对话历史）归 pikppo 客户端本地，不进入本服务。

判断准则：
- 是 LLM 该调用的外部操作（写日历、发邮件、查天气）→ 属于 pikppo-mcp
- 是用户在 UI 里操作的本地数据（建角色、改设置）→ 不属于

这条边界决定了服务的数据范围：只持久化**工具自身需要的数据**（如日历事件），不碰用户隐私性数据。

## 2. 整体架构

```
MCP 客户端（Flutter / 其它）
        │  MCP over streamable-http（或 stdio / sse）
        ▼
   BearerAuthMiddleware  ── 401 if token mismatch
        │
   FastMCP（stateless_http）
        │
   tools/      参数接收 + 工具注册（@mcp.tool，docstring 即 LLM 可见描述）
        │
   services/   业务逻辑层，委托 storage 后端
        │
   storage/    数据访问层（asyncpg 连接池，参数化 SQL）
        │
   Neon Postgres
```

分层职责严格单向依赖：

| 层 | 职责 | 约束 |
|----|------|------|
| `tools/` | 定义 MCP 工具签名与 docstring，做参数接收，调用 service | 不写业务逻辑、不直接访问数据库 |
| `services/` | 业务逻辑，编排；委托 storage 或直连外部 API | 不感知具体存储实现 |
| `storage/` | 数据访问，模型↔数据库类型互转，连接池管理 | 唯一接触 SQL 的层 |
| `models/` | Pydantic v2 数据模型，定义对外契约 | 纯数据结构 |

新增一类工具时，在 `tools/`、`services/`（+ 需持久化时加 `models/` 与 storage 表）各加一个模块即可，领域之间互不影响。service 的数据来源不限于本地存储：日历委托 storage 落 Postgres，汇率直连外部 API 不落库——这种差异被 service 层封装，对 tools 层透明。

## 3. 协议与传输

- **协议**：MCP（Model Context Protocol），框架用 mcp Python SDK 的 FastMCP。
- **传输**：默认 `streamable-http`（端点 `/mcp`），同时支持 `sse`（`/sse`）与 `stdio`。HTTP 形态供 Flutter / 远程客户端，stdio 形态供本地 MCP 客户端（如 Claude Desktop）直接拉起进程。
- **无状态（`stateless_http=True`）**：会话状态不落实例内存，任一请求可落到任意实例。这是云端水平扩容正确性的前提——多实例下用户请求可能命中不同实例，有状态会话会错乱。

> 设计约束：因为无状态，FastMCP 的 lifespan 在该模式下每请求执行一次，**不能用 lifespan 托管连接池**（并发请求会互相关闭共享池）。连接池生命周期改由 storage 层自管理（见 §5）。

## 4. 数据存储选型：Neon Postgres

**结论：用 Neon Postgres（serverless）。不用 Firestore、Cloud SQL、SQLite。**

### 4.1 选型依据

正确的比较是 serverless Postgres（Neon）vs serverless NoSQL（Firestore）——两者在运维模型、scale-to-zero、与容器平台契合度上同档。Cloud SQL 因 always-on 计费 + 连接池负担，与 serverless 架构不在一条线上，先排除。同档对齐后，唯一变量是数据模型对 pikppo 演化路径的支撑能力：

1. **当下日历数据是平局**——扁平自包含结构，document 和 relation 都能装。
2. **pikppo 愿景（私人 AI 管家、长期记忆）翻译成数据模型要求**：
   - 实体网状关系（人↔事件↔地点↔对话）→ 关系模型本命；Firestore 没 join
   - 语义检索 + 结构化条件混合查询 → pgvector + WHERE 一条 SQL；Firestore 要外挂 Vertex AI，数据物理分裂
   - 时间窗口聚合 → SQL 窗口函数原生；Firestore 聚合到 count/sum 封顶
3. **JSONB 是 document 模型的超集**——半结构化需求用 JSONB + GIN 索引覆盖，且能与关系列混合查询。
4. **Firestore 的杀手锏（客户端实时订阅 + 离线同步）在 pikppo 架构里不存在**——链路是 Flutter → MCP → DB，客户端永远不直连数据库。

### 4.2 实现要点

- 驱动：asyncpg（连接池 `min_size=0, max_size=5`），保持项目 async 风格，不引入 ORM
- 连接：Neon pooler endpoint（`-pooler` 后缀 host）；连接串放 `.env` 的 `DB_URL`，云端部署用 secret 注入
- DSN 兼容：`channel_binding` 参数 asyncpg 不识别（Neon 连接串默认携带），代码在 `storage/postgres.py:_dsn` 自动剥离
- Schema 用真实类型：`event_date DATE` / `start_time, end_time TIME` / `created_at, updated_at TIMESTAMPTZ`，`event_date` 建索引
  - `date` 是 PG 关键字，列名用 `event_date`
  - **对外契约**：Pydantic 模型与 MCP 工具是 `date: "YYYY-MM-DD"` / `time: "HH:mm"` 字符串，类型转换收在 postgres 后端内部
- 测试隔离：同一 Neon 实例下的独立 `pikppo_test` 库，每个测试前 TRUNCATE

### 4.3 连接池生命周期

连接池是 storage 层的**进程级惰性单例**（首次使用时创建，加锁防并发重复创建），生命周期与请求解耦：

- `init_schema()` / `close()` 仅供 `scripts/init-db.py`（部署前建表）和测试 teardown 使用，**不在请求路径调用**
- 建表与服务运行时彻底分离：服务启动不建表，避免 stateless 模式下并发请求触发竞态

### 4.4 数据模型

#### CalendarEvent（日历事件）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | UUID v4 |
| title | str | 事件标题 |
| date | str | 日期 YYYY-MM-DD |
| time | str? | 开始时间 HH:mm |
| end_time | str? | 结束时间 HH:mm |
| description | str? | 描述 |
| reminder_minutes | int? | 提前提醒分钟数 |

审计列 `created_at` / `updated_at`（`TIMESTAMPTZ`）由数据库维护，不暴露到模型与工具契约。

## 5. 安全设计

公网部署面向不可信网络，安全由两道独立防线构成：

1. **应用层 Bearer token 认证**（`auth.py:BearerAuthMiddleware`）：校验 `Authorization: Bearer <token>`，用 `secrets.compare_digest` 常量时间比较防时序攻击，不匹配返回 401。token 来自 `MCP_AUTH_TOKEN`。
2. **传输层 DNS rebinding 防护**（FastMCP `TransportSecuritySettings`）：Host 头白名单，默认覆盖本机 / Android 模拟器（10.0.2.2）等本地调试地址。

**fail-closed 启动校验**（`__main__.py`）：
- `MCP_ALLOWED_HOSTS=*` 关闭了 Host 白名单（云端反代场景必需，因为反代后 Host 是业务域名）时，若 `MCP_AUTH_TOKEN` 缺失则**拒绝启动**——避免 secret 挂载失误导致服务裸奔。
- 监听非回环地址但未设 token 时打印告警。

两道防线的分工：传输层防 DNS rebinding 类浏览器攻击，应用层防未授权调用。云端 ingress=all 时第一道因业务域名而放开，安全完全压在 token 上，故 token 强制存在。

## 6. 部署架构

```
mcp.pikppo.com（CNAME → ghs.googlehosted.com）
        │
   Cloud Run domain mapping（托管证书自动签发/续期）
        │
   Cloud Run 服务（asia-southeast1，0→N 自动扩缩，ingress=all）
```

- **平台**：Cloud Run（GCP 项目 `pikppo`，区域 `asia-southeast1`，与 Neon ap-southeast-1 同城新加坡）。
- **域名**：Cloud Run domain mapping 直接绑定自定义域名，托管证书自动签发/续期，无需 Load Balancer——Cloud Run 端点稳定，零额外固定费用。
- **凭证**：`DB_URL`、`MCP_AUTH_TOKEN` 走 Secret Manager；运行身份是专用最小权限 SA `pikppo-mcp@pikppo`，仅持有这两个 secret 的资源级读权限，无项目级角色。
- **长连接**：MCP streamable-http 的 SSE 长连接超时由 Cloud Run `--timeout 3600` 承担。
- **幂等**：`scripts/deploy-gcp.sh` 全程幂等，可重复执行；建表走独立的 `scripts/init-db.py`。

前置：域名首次使用前需在执行部署的 Google 账户下完成所有权验证（`gcloud domains verify`，域名级验证覆盖全部子域）。

## 7. 扩展路线

当前已实现：
- **日程管理（calendar）**——`list / get / create / update / delete` 五个工具，持久化到 Postgres。
- **汇率查询（exchange）**——`convert_currency`（按实时汇率换算金额）/ `list_exchange_rates`（某基准币种的汇率表）/ `get_exchange_trend`（日期区间内两币种每日走势 + 起止/最高/最低/涨跌幅统计）。只读不落库，双数据源：实时汇率用 open.er-api.com（免费无需 key），进程内 TTL 缓存到数据源声明的下次更新时刻（同一对话内同 base 多次换算只打一次外部 API；stateless 冷启动丢缓存则回落到 API 调用）；历史走势用 Frankfurter（免费无需 key，ECB 数据，仅工作日），按区间实时拉取不缓存。service 层封装数据源差异，工具契约一致。

按产品「应用市场」清单逐步引入：邮件、翻译、待办清单、联网搜索、地图导航、天气。每类工具是 `tools/` + `services/`（+ 需持久化时加 `models/` 与 storage 表）的一个新模块，复用同一套认证、传输、存储与部署基建，互不干扰。

## 8. 刻意不做的事

- ❌ ORM（SQLAlchemy 等）——直接参数化 SQL 已足够清晰
- ❌ 预建 `user_id` 多用户字段——确定做多用户时再加
- ❌ 为 "NoSQL feel" 把数据塞 JSONB 反范式化——该建表建表，JSONB 留给真正的半结构化字段
- ❌ pgvector 现在开启——等接入记忆 embedding 检索时再 `CREATE EXTENSION vector;`（Neon first-class 支持，路径是通的）

## 运行时注意

- Neon cold start 首条 SQL ~500ms–1s，在 LLM 对话延迟（秒级）里会被吸收
- 健康检查端点不要触发 DB 连接，避免把 Neon 一直唤醒消耗免费层 compute hours
