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
- **数据库**: SQLite（aiosqlite 异步访问）— 仅用于外部工具自身需要持久化的数据（如日历事件）
- **数据验证**: Pydantic v2

## 项目结构

```
pikppo-mcp/
├── CLAUDE.md
├── pyproject.toml
├── start.sh                     # 一键启动脚本
├── src/
│   └── app/
│       ├── __init__.py
│       ├── __main__.py          # python -m app 入口
│       ├── server.py            # FastMCP 实例、lifespan、Host 白名单
│       ├── database.py          # SQLite 连接与初始化
│       ├── models/              # Pydantic 数据模型（仅外部工具相关）
│       │   ├── __init__.py
│       │   └── calendar_event.py
│       ├── tools/               # MCP 工具定义（按工具拆分）
│       │   ├── __init__.py
│       │   └── calendar.py
│       └── services/            # 业务逻辑层
│           ├── __init__.py
│           └── calendar_service.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_calendar.py
└── data/                        # 运行时数据（git 忽略 *.db）
    └── pikppo.db
```

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
- tools 层只做参数接收与工具注册，业务逻辑放在 services 层
- 数据模型统一使用 Pydantic v2
- 数据库操作使用 aiosqlite 异步访问
- 所有 ID 使用 UUID v4 字符串
- 时间戳统一使用毫秒级整数
- 日期格式 `YYYY-MM-DD`，时间格式 `HH:mm`
- 工具的 docstring 即 LLM 看到的工具描述，需清晰准确

## 启动方式

推荐使用脚本：

```bash
./start.sh                  # streamable-http @ 127.0.0.1:8000
./start.sh --inspect        # 同时启动 MCP Inspector 并预填连接参数
./start.sh --host 0.0.0.0   # 监听全网卡（供 Android 模拟器 10.0.2.2 / 局域网真机访问）
./start.sh --transport sse  # 切换传输协议（stdio | sse | streamable-http）
```

或直接：

```bash
pip install -e ".[dev]"
python -m app                # 默认 streamable-http :8000
```

服务端已配置 Host 白名单（含 `127.0.0.1` / `localhost` / `10.0.2.2`），如需追加局域网地址：

```bash
MCP_ALLOWED_HOSTS="192.168.1.10:8000" ./start.sh --host 0.0.0.0
```

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
