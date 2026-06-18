# pikppo-mcp 技术方案

pikppo 的**外部工具** MCP 服务：通过 MCP 协议向 pikppo Flutter 客户端及任意 MCP 兼容客户端暴露可被 LLM 调用的外挂能力（汇率、邮件、翻译、地图、天气……）。本文记录整体架构、关键选型与设计依据；面向开发的操作规范见 `CLAUDE.md`。

## 1. 定位与边界

服务只承载**外部工具**——LLM 该主动调用、用于操作真实世界服务的能力。app 自身的内在能力（记忆、角色、群组、用户设置、对话历史）以及**个人领域数据（日历、笔记、待办、联系人…）**归 pikppo 客户端本地，不进入本服务。

判断准则：
- 是 LLM 该调用的外部操作（发邮件、查天气、查汇率——访问第三方系统 / 跨用户共享 / 需服务端算力或密钥）→ 属于 pikppo-mcp
- 是用户的个人领域数据或 UI 本地操作（日历、笔记、建角色、改设置）→ 不属于

> **local-first 边界**：个人领域数据的真相源在客户端本地个人数据存储，跨设备同步由该存储层统一负责（加密 blob / CRDT / 零知识服务端），**不为每个领域在服务端各开一套 CRUD**。「LLM 从对话创建日程」这类价值仍保留，但落点是写入本地存储，不是服务端工具——能力归属看外部操作的实现该挂在哪一层，而非该不该让 LLM 调。

这条边界决定了服务的数据范围：服务端只在**外部工具自身确需落库**时持久化（跨用户共享、服务端缓存、第三方集成状态等），不碰个人领域数据与用户隐私数据。

## 2. 整体架构

```
MCP 客户端（Flutter / 其它）
        │  MCP over streamable-http（或 stdio / sse）
        ▼
   BearerAuthMiddleware  ── 401 if token mismatch
        │
   FastMCP（stateless_http）
        │
   tools/      参数接收 + 工具注册（@mcp.tool 显式 name/title/description + 参数 Field）
        │
   services/   业务逻辑层，委托 storage 后端或直连外部 API
        │
   storage/    中性持久化框架（asyncpg 连接池，参数化 SQL；当前无领域表）
        │
   Neon Postgres
```

分层职责严格单向依赖：

| 层 | 职责 | 约束 |
|----|------|------|
| `tools/` | 定义 MCP 工具签名与三字段描述，做参数接收，调用 service | 不写业务逻辑、不直接访问数据库 |
| `services/` | 业务逻辑，编排；委托 storage 或直连外部 API | 不感知具体存储实现 |
| `storage/` | 数据访问，模型↔数据库类型互转，连接池管理 | 唯一接触 SQL 的层 |
| `models/` | Pydantic v2 数据模型，定义对外契约 | 纯数据结构 |

新增一类工具时，在 `tools/`、`services/`（+ 需服务端落库时加 `models/` 与 storage 表）各加一个模块即可，领域之间互不影响。service 的数据来源不限：需落库的工具委托 storage，汇率等只读工具直连外部 API 不落库——这种差异被 service 层封装，对 tools 层透明。

## 3. 协议与传输

- **协议**：MCP（Model Context Protocol），框架用 mcp Python SDK 的 FastMCP。
- **传输**：默认 `streamable-http`（端点 `/mcp`），同时支持 `sse`（`/sse`）与 `stdio`。HTTP 形态供 Flutter / 远程客户端，stdio 形态供本地 MCP 客户端（如 Claude Desktop）直接拉起进程。
- **无状态（`stateless_http=True`）**：会话状态不落实例内存，任一请求可落到任意实例。这是云端水平扩容正确性的前提——多实例下用户请求可能命中不同实例，有状态会话会错乱。

> 设计约束：因为无状态，FastMCP 的 lifespan 在该模式下每请求执行一次，**不能用 lifespan 托管连接池**（并发请求会互相关闭共享池）。连接池生命周期改由 storage 层自管理（见 §5）。

## 4. 工具描述契约

每个工具用 `@mcp.tool(name=, title=, description=)` **显式声明三字段**，不依赖默认推断：

- `name`：对外工具名（MCP `tools/list` 的 `name`），与 Python 函数名解耦
- `title`：人类可读展示名（客户端 UI 显示），如「货币换算」「汇率走势」
- `description`：LLM 看到的工具描述，一行简述

参数的格式约束（ISO 4217、`YYYY-MM-DD` 等）用 `Annotated[T, Field(description=...)]` 写在函数签名上，进入 `inputSchema.properties.*.description`。

> 此版本 mcp SDK **不解析 docstring 的 `Args:`** 进逐参数描述——实测验证过：裸 `@mcp.tool()` 时 docstring 整体（含 Args 文本）只进工具级描述，一旦用显式 `description=` 覆盖，参数提示就随之消失。故参数提示一律走 `Field`，与工具级 `description` 解耦，跨 SDK 版本稳定。

## 5. 数据存储：Neon Postgres（休眠的中性框架）

**结论：保留 Neon Postgres（serverless）作为休眠的中性持久化框架，当前无任何领域表。** 不用 Firestore、Cloud SQL、SQLite。

> **local-first 修正**：本服务最初的落库驱动是日历事件，并设想把「私人 AI 管家 / 长期记忆」也放服务端。`§1` 的 local-first 边界推翻了后者——个人领域数据与记忆归客户端本地存储，跨设备同步是本地存储层一件事，不需要每个领域在服务端各建一套 CRUD。日历领域已整体撤出（表、CRUD、模型、工具全删）。Postgres 基建（连接池 / DSN 处理 / 迁移机制）已调通验证，作为**零业务语义的可复用资产保留**，待真正需要服务端落库的外部工具出现时挂表启用。

### 5.1 为何保留而非删除或换 NoSQL

未来若有外部工具需服务端落库，Postgres 仍是默认选择，理由不依赖已撤出的个人数据：

- serverless Postgres（Neon）与 Cloud Run 同档：scale-to-zero、与容器平台契合；Cloud SQL 因 always-on 计费 + 连接池负担先排除
- 关系模型 + JSONB + （需要时）pgvector 覆盖结构化 / 半结构化 / 向量检索三类需求于一条 SQL，避免数据物理分裂
- 基建沉没成本为零、重建成本不低：环境、依赖、部署 secret 都已趟平，删掉再从头调一遍远不止改几行代码——保留一个干净空框架优于反复拆建

### 5.2 框架要点（已就位，无领域表）

- 驱动：asyncpg（连接池 `min_size=0, max_size=5`），保持 async 风格，不引入 ORM
- 连接：Neon pooler endpoint（`-pooler` 后缀 host）；`DB_URL` 放 `.env`，云端部署用 secret 注入
- DSN 兼容：`channel_binding` 参数 asyncpg 不识别（Neon 连接串默认携带），代码在 `storage/postgres.py:_dsn` 自动剥离
- `SCHEMA` 当前为空字符串，`init_schema()` 对空 SCHEMA 直接 no-op、不连库；新增领域表时把 DDL 追加到 `SCHEMA`（真实类型 `DATE`/`TIME`/`TIMESTAMPTZ` + `created_at`/`updated_at` 审计列）并重跑 `scripts/init-db.py`
- 对外契约约定（保留为未来规范）：日期/时间在模型与工具契约里用字符串（`YYYY-MM-DD` / `HH:mm`），与 PG 真实类型的互转收在 storage 后端内部；审计列由数据库维护，不暴露到模型与工具契约

### 5.3 连接池生命周期

连接池是 storage 层的**进程级惰性单例**（首次使用时创建，加锁防并发重复创建），生命周期与请求解耦：

- `init_schema()` / `close()` 仅供 `scripts/init-db.py`（部署前迁移）和测试 teardown 使用，**不在请求路径调用**
- 迁移与服务运行时彻底分离：服务启动不建表，避免 stateless 模式下并发请求触发竞态
- 当前无领域表、无 storage caller，连接池在运行时不会被创建（惰性），故服务实际无状态运行

## 6. 安全设计

公网部署面向不可信网络，安全由两道独立防线构成：

1. **应用层 Bearer token 认证**（`auth.py:BearerAuthMiddleware`）：校验 `Authorization: Bearer <token>`，用 `secrets.compare_digest` 常量时间比较防时序攻击，不匹配返回 401。token 来自 `MCP_AUTH_TOKEN`。
2. **传输层 DNS rebinding 防护**（FastMCP `TransportSecuritySettings`）：Host 头白名单，默认覆盖本机 / Android 模拟器（10.0.2.2）等本地调试地址。

**fail-closed 启动校验**（`__main__.py`）：
- `MCP_ALLOWED_HOSTS=*` 关闭了 Host 白名单（云端反代场景必需，因为反代后 Host 是业务域名）时，若 `MCP_AUTH_TOKEN` 缺失则**拒绝启动**——避免 secret 挂载失误导致服务裸奔。
- 监听非回环地址但未设 token 时打印告警。

两道防线的分工：传输层防 DNS rebinding 类浏览器攻击，应用层防未授权调用。云端 ingress=all 时第一道因业务域名而放开，安全完全压在 token 上，故 token 强制存在。

## 7. 部署架构

```
mcp.pikppo.com（CNAME → ghs.googlehosted.com）
        │
   Cloud Run domain mapping（托管证书自动签发/续期）
        │
   Cloud Run 服务（asia-southeast1，0→N 自动扩缩，ingress=all）
```

- **平台**：Cloud Run（GCP 项目 `pikppo`，区域 `asia-southeast1`，与 Neon ap-southeast-1 同城新加坡）。
- **域名**：Cloud Run domain mapping 直接绑定自定义域名，托管证书自动签发/续期，无需 Load Balancer——Cloud Run 端点稳定，零额外固定费用。
- **凭证**：`DB_URL`、`MCP_AUTH_TOKEN` 走 Secret Manager；运行身份是专用最小权限 SA `pikppo-mcp@pikppo`，仅持有这两个 secret 的资源级读权限，无项目级角色。（`DB_URL` 为框架接入点，当前无表时运行时不连库。）
- **长连接**：MCP streamable-http 的 SSE 长连接超时由 Cloud Run `--timeout 3600` 承担。
- **幂等**：`scripts/deploy-gcp.sh` 全程幂等，可重复执行；迁移走独立的 `scripts/init-db.py`（当前 SCHEMA 为空即空操作）。

前置：域名首次使用前需在执行部署的 Google 账户下完成所有权验证（`gcloud domains verify`，域名级验证覆盖全部子域）。

## 8. 扩展路线

当前已实现：
- **汇率查询（exchange）**——`convert_currency`（按实时汇率换算金额）/ `list_exchange_rates`（某基准币种的汇率表）/ `get_exchange_trend`（日期区间内两币种每日走势 + 起止/最高/最低/涨跌幅统计）。只读不落库，双数据源：实时汇率用 open.er-api.com（免费无需 key），进程内 TTL 缓存到数据源声明的下次更新时刻（同一对话内同 base 多次换算只打一次外部 API；stateless 冷启动丢缓存则回落到 API 调用）；历史走势用 Frankfurter（免费无需 key，ECB 数据，仅工作日），按区间实时拉取不缓存。service 层封装数据源差异，工具契约一致。

按产品「应用市场」清单逐步引入：邮件、翻译、待办清单、联网搜索、地图导航、天气。每类工具是 `tools/` + `services/`（+ 需服务端落库时加 `models/` 与 storage 表）的一个新模块，复用同一套认证、传输、存储与部署基建，互不干扰。

> 注意区分：「待办清单」等若是**用户个人领域数据**，按 §1 边界归客户端本地存储，不做成服务端工具；只有访问第三方系统 / 跨用户共享 / 需服务端算力的能力才进本服务。

## 9. 刻意不做的事

- ❌ ORM（SQLAlchemy 等）——直接参数化 SQL 已足够清晰
- ❌ 预建 `user_id` 多用户字段——确定做多用户时再加
- ❌ 为 "NoSQL feel" 把数据塞 JSONB 反范式化——该建表建表，JSONB 留给真正的半结构化字段
- ❌ pgvector 现在开启——等真正需要服务端向量检索的外部工具出现时再 `CREATE EXTENSION vector;`（Neon first-class 支持，路径是通的；个人记忆的向量检索属客户端本地，不在此）

## 运行时注意

- Neon cold start 首条 SQL ~500ms–1s——当前无领域表故运行时不触发；未来挂表后该延迟在 LLM 对话延迟（秒级）里会被吸收
- 健康检查端点不要触发 DB 连接，避免把 Neon 一直唤醒消耗免费层 compute hours
