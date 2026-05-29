# pikppo-mcp

pikppo 的 MCP 服务，为 pikppo Flutter 客户端提供工具调用能力。

## 项目定位

作为 [pikppo](../pikppo)（多角色 AI 私人管家应用）的 MCP Server，通过 MCP 协议暴露工具（tools），供 LLM 调用以完成：
- 角色管理（AI 助手人设）
- 日程管理（日历事件 CRUD）
- 记忆管理（语义/情景/工作记忆）
- 群组管理（多角色群聊）
- 用户配置

## 技术栈

- **语言**: Python 3.11+
- **协议**: MCP（Model Context Protocol）
- **框架**: mcp Python SDK（FastMCP）
- **数据库**: SQLite（通过 aiosqlite 异步访问）
- **数据验证**: Pydantic v2

## 项目结构

```
pikppo-api/
├── AGENTS.md
├── pyproject.toml               # 项目元数据与依赖
├── .gitignore
├── src/                         # 正式代码
│   └── app/
│       ├── __init__.py
│       ├── __main__.py          # python -m app 入口
│       ├── server.py            # MCP Server 实例与 lifespan
│       ├── database.py          # 数据库连接与初始化
│       ├── models/              # Pydantic 数据模型
│       │   ├── __init__.py
│       │   ├── role.py
│       │   ├── calendar_event.py
│       │   ├── memory.py
│       │   ├── group.py
│       │   └── user.py
│       ├── tools/               # MCP 工具定义（按领域拆分）
│       │   ├── __init__.py
│       │   ├── roles.py         # 角色管理工具
│       │   ├── calendar.py      # 日程管理工具
│       │   ├── memories.py      # 记忆管理工具
│       │   ├── groups.py        # 群组管理工具
│       │   └── users.py         # 用户配置工具
│       └── services/            # 业务逻辑层（数据库操作）
│           ├── __init__.py
│           ├── role_service.py
│           ├── calendar_service.py
│           ├── memory_service.py
│           ├── group_service.py
│           └── user_service.py
├── tests/                       # 测试代码
│   ├── __init__.py
│   ├── conftest.py
│   └── test_*.py
└── data/                        # 运行时数据（git 忽略 *.db）
    └── pikppo.db
```

## MCP 工具清单

### 角色管理
| 工具 | 说明 |
|------|------|
| `list_roles` | 获取所有角色 |
| `create_role` | 创建自定义角色 |
| `update_role` | 更新角色信息 |
| `delete_role` | 删除自定义角色 |

### 日程管理
| 工具 | 说明 |
|------|------|
| `list_calendar_events` | 查询事件（支持日期范围筛选） |
| `get_calendar_event` | 获取单个事件详情 |
| `create_calendar_event` | 创建事件 |
| `update_calendar_event` | 更新事件 |
| `delete_calendar_event` | 删除事件 |

### 记忆管理
| 工具 | 说明 |
|------|------|
| `list_memories` | 查询记忆（支持类型/标签筛选） |
| `create_memory` | 创建记忆 |
| `update_memory` | 更新记忆 |
| `delete_memory` | 删除单条记忆 |
| `clear_memories` | 清空所有记忆 |

### 群组管理
| 工具 | 说明 |
|------|------|
| `list_groups` | 获取所有群组 |
| `create_group` | 创建群组 |
| `update_group` | 更新群组 |
| `delete_group` | 删除群组 |

### 用户配置
| 工具 | 说明 |
|------|------|
| `get_user_profile` | 获取用户配置 |
| `update_user_profile` | 更新用户配置 |

## 数据模型

### Role（角色）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | UUID |
| name | str | 角色名称 |
| icon | str | emoji 图标 |
| description | str | 角色描述 |
| color | int | 颜色值 |
| system_prompt | str | 系统提示词 |
| is_default | bool | 是否为内置角色 |
| created_at | int | 创建时间戳(ms) |

### CalendarEvent（日历事件）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | UUID |
| title | str | 事件标题 |
| date | str | 日期 YYYY-MM-DD |
| time | str? | 时间 HH:mm |
| end_time | str? | 结束时间 HH:mm |
| description | str? | 描述 |
| reminder_minutes | int? | 提前提醒分钟数 |

### Memory（记忆）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | UUID |
| type | enum | semantic / episodic / working |
| content | str | 记忆内容 |
| role_id | str? | 关联角色 |
| tags | list[str] | 标签 |
| timestamp | int | 时间戳(ms) |

### Group（群组）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | UUID |
| name | str | 群组名称 |
| role_ids | list[str] | 成员角色 ID |

## 开发规范

- tools 层只做参数接收和工具注册，业务逻辑放在 services 层
- 数据模型统一使用 Pydantic v2
- 数据库操作使用 aiosqlite 异步访问
- 所有 ID 使用 UUID v4 字符串
- 时间戳统一使用毫秒级整数
- 日期格式 YYYY-MM-DD，时间格式 HH:mm
- 工具的 docstring 即为 LLM 看到的工具描述，需清晰准确

## 启动方式

```bash
cd pikppo-mcp
pip install -e ".[dev]"
python -m app
```

## 客户端配置

在 MCP 客户端（如 Codex Desktop）中添加：

```json
{
  "mcpServers": {
    "pikppo": {
      "command": "python",
      "args": ["-m", "app"],
      "cwd": "/path/to/pikppo-mcp"
    }
  }
}
```
