# pikppo-mcp

pikppo 的 **外部工具** MCP 服务，通过 MCP 协议向 pikppo Flutter 客户端及任意 MCP 兼容客户端暴露**外挂能力**，供 LLM 调用以操作真实世界的服务（日程、邮件、翻译、地图、天气……）。

## 项目定位与边界

参考 [pikppo 产品方案设计](../pikppo/docs/产品方案设计.md) 第 3.4 / 4.3 节：

> **应用页只放外部工具（通过 MCP 接入），不放 app 核心功能（记忆、角色等）。**
> **记忆是 app 内在能力，不是外挂工具。**
> **app 只做对话和记忆，工具通过 MCP 独立。**

由此本仓库的边界**仅包含外部工具**。下面这些**不属于** pikppo-mcp 的职责：

| 能力 | 归属 | 原因 |
|------|------|------|
| 角色（Role）管理 | pikppo 客户端本地 | app 的人设系统，由 UI 维护，不由 LLM 调用 |
| 群组（Group）管理 | pikppo 客户端本地 | 群聊结构属于聊天界面本体 |
| 记忆（Memory）管理 | pikppo 客户端本地 | 设计原则「记忆归用户所有」，本地存储默认；远程同步由客户端自行实现 |
| 用户设置 / 用户画像 | pikppo 客户端本地 | 配置由 UI 维护；画像由客户端从对话归纳 |
| 对话 / 消息历史 | pikppo 客户端本地 | 隐私边界、上下文构建由客户端负责 |

判断一个能力是否归 pikppo-mcp：
- **是不是 LLM 该调用的外部操作？**（写日历、发邮件、查天气）→ 是
- **是不是用户在 UI 里操作的本地数据？**（建角色、改设置）→ 否

## 技术栈

- **语言**: Python 3.11+
- **协议**: MCP（Model Context Protocol）
- **框架**: mcp Python SDK（FastMCP）
- **数据库**: Neon Postgres（serverless，asyncpg 异步访问）— 仅用于外部工具自身需要持久化的数据（如日历事件）；连接串放 `.env` 的 `DB_URL`，测试用同实例下的独立 `pikppo_test` 库
- **数据验证**: Pydantic v2

## 项目结构

```
pikppo-mcp/
├── CLAUDE.md
├── pyproject.toml
├── uv.lock                      # 依赖锁定（升级依赖：uv lock --upgrade，需提交）
├── Dockerfile                   # 云端部署镜像
├── scripts/
│   ├── start.sh                 # 一键启动脚本
│   ├── init-db.py               # 初始化数据库 schema（部署前对目标库执行一次，幂等）
│   ├── deploy-gcp.sh            # 一键部署：Cloud Build → Cloud Run → domain mapping 绑定域名
│   └── cloudbuild.yaml          # Cloud Build 构建配置
├── .env                         # DB_URL 等敏感配置（git 忽略）
├── docs/
│   └── technical-design.md      # 技术方案（架构 / 选型 / 安全 / 部署）
├── src/
│   └── app/
│       ├── __init__.py          # 加载 .env
│       ├── __main__.py          # python -m app 入口（读 $PORT，挂认证中间件）
│       ├── server.py            # FastMCP 实例（stateless_http）、Host 白名单 / DNS rebinding 防护
│       ├── auth.py              # Bearer token 认证中间件（MCP_AUTH_TOKEN）
│       ├── storage/             # 数据访问层
│       │   ├── __init__.py
│       │   └── postgres.py      # Neon Postgres（asyncpg 连接池）
│       ├── models/              # Pydantic 数据模型（仅外部工具相关）
│       │   ├── __init__.py
│       │   └── calendar_event.py
│       ├── tools/               # MCP 工具定义（按工具拆分）
│       │   ├── __init__.py
│       │   └── calendar.py
│       └── services/            # 业务逻辑层（委托 storage 后端）
│           ├── __init__.py
│           └── calendar_service.py
└── tests/
    ├── __init__.py
    ├── conftest.py              # 测试连同实例下的 pikppo_test 库，每测试 TRUNCATE
    └── test_calendar.py
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `DB_URL` | Neon Postgres 连接串（放 `.env`，必需）；`channel_binding` 参数会被自动剥离（asyncpg 不支持） |
| `MCP_AUTH_TOKEN` | 设置后启用 Bearer token 认证（HTTP 传输），公网部署必须设置 |
| `MCP_ALLOWED_HOSTS` | 追加 Host 白名单（逗号分隔）；设为 `*` 关闭 DNS rebinding 防护（云端反代场景，需配合 token 认证） |
| `PORT` | HTTP 监听端口（Cloud Run 等平台注入），默认 8000 |

## MCP 工具清单

### 日程管理（calendar）

| 工具 | 说明 |
|------|------|
| `list_calendar_events` | 查询事件（支持日期范围筛选） |
| `get_calendar_event` | 获取单个事件详情 |
| `create_calendar_event` | 创建事件 |
| `update_calendar_event` | 更新事件 |
| `delete_calendar_event` | 删除事件 |

### 规划中

按设计文档「应用市场」清单，后续逐步引入：
- 📧 邮件（收发、摘要、智能回复）
- 🌐 翻译
- ✅ 待办清单
- 🔍 联网搜索
- 🗺️ 地图导航
- ☀️ 天气

每新增一类工具，只需在 `tools/`、`services/`、`models/` 各加一个模块，不改动其他领域。

## 数据模型

仅外部工具自身需要持久化的数据。

### CalendarEvent（日历事件）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | UUID v4 |
| title | str | 事件标题 |
| date | str | 日期 YYYY-MM-DD |
| time | str? | 时间 HH:mm |
| end_time | str? | 结束时间 HH:mm |
| description | str? | 描述 |
| reminder_minutes | int? | 提前提醒分钟数 |

## 开发规范

- **边界优先**：新增任何工具前，先按上文「判断原则」确认是否属于 pikppo-mcp 范畴；属于客户端本体的能力**不要**做成 MCP 工具
- tools 层只做参数接收与工具注册，业务逻辑放在 services 层，数据访问放在 storage 后端
- 数据模型统一使用 Pydantic v2
- 数据库用 asyncpg 直接写参数化 SQL，不用 ORM；新表用真实类型（DATE/TIME/TIMESTAMPTZ）+ created_at/updated_at 审计列；schema 变更同步到 `storage/postgres.py` 的 `SCHEMA` 并重跑 `scripts/init-db.py`
- 依赖以 `uv.lock` 为准（镜像内 `uv sync --frozen`）；增删依赖后必须 `uv lock` 并提交 lock 文件
- 所有 ID 使用 UUID v4 字符串
- 对外契约里日期/时间一律用字符串：日期 `YYYY-MM-DD`、时间 `HH:mm`；与 PG 真实 DATE/TIME 类型的互转收在 storage 后端内部，模型层不感知
- 审计列 `created_at` / `updated_at`（`TIMESTAMPTZ`）由数据库维护，不暴露到 Pydantic 模型与工具契约
- 工具的 docstring 即 LLM 看到的工具描述，需清晰准确

## 启动方式

推荐使用脚本：

```bash
scripts/start.sh                  # streamable-http @ 127.0.0.1:8000
scripts/start.sh --inspect        # 同时启动 MCP Inspector 并预填连接参数
scripts/start.sh --host 0.0.0.0   # 监听全网卡（供 Android 模拟器 10.0.2.2 / 局域网真机访问）
scripts/start.sh --transport sse  # 切换传输协议（stdio | sse | streamable-http）
```

或直接：

```bash
pip install -e ".[dev]"
python -m app                # 默认 streamable-http :8000
```

服务端已配置 Host 白名单（含 `127.0.0.1` / `localhost` / `10.0.2.2`），如需追加局域网地址：

```bash
MCP_ALLOWED_HOSTS="192.168.1.10:8000" scripts/start.sh --host 0.0.0.0
```

## 部署（Cloud Run + domain mapping）

```bash
python scripts/init-db.py              # 首次部署前建表（幂等；建表不在服务运行时路径）
bash scripts/deploy-gcp.sh             # 构建镜像 + 部署 + 绑定域名（默认）
bash scripts/deploy-gcp.sh --no-build  # 跳过构建，复用已有镜像
DOMAIN=mcp.example.com bash scripts/deploy-gcp.sh  # 自定义域名
```

架构：`mcp.pikppo.com`（CNAME → `ghs.googlehosted.com`）→ Cloud Run domain mapping → Cloud Run（0→N 自动扩缩，公网入口 ingress=all）。无需 Load Balancer：Cloud Run 端点稳定，域名直接由 domain mapping 绑定、托管证书自动签发，零额外固定费用。

要点：
- GCP 项目 `pikppo`，区域 `asia-southeast1`（与 Neon ap-southeast-1 同城）
- 脚本幂等可重复执行；secrets（`DB_URL`、`MCP_AUTH_TOKEN`）走 Secret Manager，运行身份用专用最小权限 SA `pikppo-mcp@pikppo`（仅两个 secret 的资源级读权限）
- 服务端 `stateless_http=True`：会话不落实例内存，请求可落任意实例，多实例扩容安全
- 连接池是 storage 层惰性进程级单例，自管理生命周期；**不要给 FastMCP 传 lifespan 管理池**（stateless 模式下 lifespan 每请求执行，会引发并发关池竞态）；建表只走 `scripts/init-db.py`，不在请求路径
- ingress=all 公网可直达，安全完全依赖应用层 `MCP_AUTH_TOKEN`（fail-closed：`MCP_ALLOWED_HOSTS=*` 关闭 Host 白名单时 token 缺失则拒绝启动）；公网部署务必设置该 token
- 自定义域名经反代到达，Host 头为 `mcp.pikppo.com`，故云端部署设 `MCP_ALLOWED_HOSTS=*` 关闭 DNS rebinding 防护（由 token 兜底）
- domain mapping 走 `gcloud beta run domain-mappings`，托管证书自动签发/续期；首次部署后按脚本输出的 DNS 记录（CNAME → `ghs.googlehosted.com`）配置，DNS 生效后约 15-60 分钟证书转 ACTIVE
- 域名首次使用前需在执行部署的 Google 账户下完成所有权验证（`gcloud domains verify pikppo.com`，域名级验证覆盖全部子域）

## 客户端配置

### pikppo Flutter 客户端

在 pikppo「设置 → MCP 服务地址」填：
- 本机调试：`http://127.0.0.1:8000/mcp`
- Android 模拟器：`http://10.0.2.2:8000/mcp`（server 需 `--host 0.0.0.0`）
- 局域网真机：`http://<宿主机 LAN IP>:8000/mcp`（host 同上 + 加入白名单）

### 其它 MCP 客户端（stdio）

```json
{
  "mcpServers": {
    "pikppo": {
      "command": "python",
      "args": ["-m", "app", "--transport", "stdio"],
      "cwd": "/path/to/pikppo-mcp"
    }
  }
}
```
