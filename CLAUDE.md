# pikppo-api

pikppo 的后端 API 服务，基于 FastAPI，为 pikppo Flutter 客户端提供功能接口。

## 项目定位

为 pikppo（多角色 AI 私人管家应用）提供 HTTP API 服务，核心功能包括：
- 角色管理（AI 助手人设）
- 日程管理（日历事件 CRUD）
- 记忆管理（语义/情景/工作记忆）
- 群组管理（多角色群聊）
- 用户配置

## 技术栈

- **语言**: Python 3.11+
- **框架**: FastAPI + Uvicorn
- **数据库**: SQLite（通过 aiosqlite 异步访问）
- **数据验证**: Pydantic v2

## 项目结构

```
pikppo-api/
├── CLAUDE.md
├── pyproject.toml               # 项目元数据与依赖
├── .gitignore
├── src/                         # 正式代码
│   └── app/
│       ├── __init__.py
│       ├── main.py              # 应用入口，创建 FastAPI 实例并挂载路由
│       ├── database.py          # 数据库连接与初始化
│       ├── models/              # Pydantic 数据模型
│       │   ├── __init__.py
│       │   ├── role.py          # 角色模型
│       │   ├── calendar_event.py# 日历事件模型
│       │   ├── memory.py        # 记忆模型
│       │   ├── group.py         # 群组模型
│       │   └── user.py          # 用户配置模型
│       ├── routers/             # API 路由（按领域拆分）
│       │   ├── __init__.py
│       │   ├── roles.py         # /api/roles
│       │   ├── calendar.py      # /api/calendar/events
│       │   ├── memories.py      # /api/memories
│       │   ├── groups.py        # /api/groups
│       │   └── users.py         # /api/users
│       └── services/            # 业务逻辑层
│           ├── __init__.py
│           ├── role_service.py
│           ├── calendar_service.py
│           ├── memory_service.py
│           ├── group_service.py
│           └── user_service.py
└── tests/                       # 测试代码
    ├── __init__.py
    ├── conftest.py              # pytest fixtures
    └── test_*.py
```

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

## API 设计

所有接口前缀：`/api`

### 角色 `/api/roles`
```
GET    /api/roles              # 获取所有角色
POST   /api/roles              # 创建自定义角色
PUT    /api/roles/{id}         # 更新角色
DELETE /api/roles/{id}         # 删除角色（仅自定义）
```

### 日程 `/api/calendar/events`
```
GET    /api/calendar/events              # 查询事件（支持 ?start_date=&end_date= 筛选）
GET    /api/calendar/events/{id}         # 获取单个事件
POST   /api/calendar/events              # 创建事件
PUT    /api/calendar/events/{id}         # 更新事件
DELETE /api/calendar/events/{id}         # 删除事件
```

### 记忆 `/api/memories`
```
GET    /api/memories                     # 查询记忆（支持 ?type=&tags= 筛选）
POST   /api/memories                     # 创建记忆
PUT    /api/memories/{id}                # 更新记忆
DELETE /api/memories/{id}                # 删除单条
DELETE /api/memories                     # 清空所有记忆
```

### 群组 `/api/groups`
```
GET    /api/groups                       # 获取所有群组
POST   /api/groups                       # 创建群组
PUT    /api/groups/{id}                  # 更新群组
DELETE /api/groups/{id}                  # 删除群组
```

### 用户 `/api/users`
```
GET    /api/users/profile                # 获取用户配置
PUT    /api/users/profile                # 更新用户配置
```

## 统一响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

错误响应：
```json
{
  "code": 40001,
  "message": "角色不存在",
  "data": null
}
```

## 开发规范

- 路由层（routers）只做参数接收和响应返回，业务逻辑放在 services 层
- 数据模型统一使用 Pydantic v2，区分请求模型（XxxCreate/XxxUpdate）和响应模型（Xxx）
- 数据库操作使用 aiosqlite 异步访问
- 所有 ID 使用 UUID v4 字符串
- 时间戳统一使用毫秒级整数
- 日期格式 YYYY-MM-DD，时间格式 HH:mm

## 启动方式

```bash
cd pikppo-api
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

API 文档：`http://localhost:8000/docs`