# 数据库选型决策：Neon Postgres

**结论：用 Neon Postgres（serverless）。不用 Firestore、Cloud SQL、SQLite。**

## 为什么

正确的比较是 serverless Postgres (Neon) vs serverless NoSQL (Firestore)——两者在运维模型、scale-to-zero、与容器平台契合度上同档。Cloud SQL 因 always-on 计费 + 连接池负担，与 serverless 架构不在一条线上，先排除。同档对齐后，唯一变量是数据模型对 pikppo 演化路径的支撑能力：

1. **当下日历数据是平局**——扁平自包含结构，document 和 relation 都能装。
2. **pikppo 愿景（私人 AI 管家、长期记忆）翻译成数据模型要求**：
   - 实体网状关系（人↔事件↔地点↔对话）→ 关系模型本命；Firestore 没 join
   - 语义检索 + 结构化条件混合查询 → pgvector + WHERE 一条 SQL；Firestore 要外挂 Vertex AI，数据物理分裂
   - 时间窗口聚合 → SQL 窗口函数原生；Firestore 聚合到 count/sum 封顶
3. **JSONB 是 document 模型的超集**——半结构化需求用 JSONB + GIN 索引覆盖，且能与关系列混合查询。
4. **Firestore 的杀手锏（客户端实时订阅 + 离线同步）在 pikppo 架构里不存在**——链路是 Flutter → MCP → DB，客户端永远不直连数据库。

## 实现要点（已落地）

- 驱动：asyncpg（连接池 `min_size=0, max_size=5`），保持项目 async 风格，不引入 ORM
- 连接：Neon pooler endpoint（`-pooler` 后缀 host）；连接串放 `.env` 的 `DB_URL`，云端部署用 secret 注入
- DSN 兼容：`channel_binding` 参数 asyncpg 不识别，代码自动剥离（`storage/postgres.py:_dsn`）
- Schema 用真实类型：`event_date DATE` / `start_time, end_time TIME` / `created_at, updated_at TIMESTAMPTZ`，`event_date` 建索引
  - `date` 是 PG 关键字，列名用 `event_date`
  - **对外契约不变**：Pydantic 模型与 MCP 工具仍是 `date: "YYYY-MM-DD"` / `time: "HH:mm"` 字符串，类型转换收在 postgres 后端内部
- 测试隔离：同一 Neon 实例下的独立 `pikppo_test` 库，每个测试前 TRUNCATE；不保留 sqlite 后端（2026-06-10 移除）

## 刻意不做的事

- ❌ ORM（SQLAlchemy 等）——直接参数化 SQL 已足够清晰
- ❌ 预建 `user_id` 多用户字段——确定做多用户时再加
- ❌ 为 "NoSQL feel" 把数据塞 JSONB 反范式化——该建表建表，JSONB 留给真正的半结构化字段
- ❌ pgvector 现在开启——等接入记忆 embedding 检索时再 `CREATE EXTENSION vector;`（Neon first-class 支持，路径是通的）

## 运行时注意

- Neon cold start 首条 SQL ~500ms–1s，在 LLM 对话延迟（秒级）里会被吸收
- 健康检查端点不要触发 DB 连接，避免把 Neon 一直唤醒消耗免费层 compute hours
