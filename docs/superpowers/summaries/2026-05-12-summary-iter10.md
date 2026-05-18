---
iteration: 10
phase: "dev-loop + summarize"
date: 2026-05-12
status: complete
previous: summaries/2026-05-12-summary-iter9.md
---

# 总结报告 — 2026-05-12 (Iteration 10)

## A. 本轮完成

- 实现知识库创建全链路：数据模型 → API → 前端页面 → 聊天中选择（按 plan 完成 F-1~F-6）
- 知识库数据模型 + aiosqlite 异步存储（KnowledgeBase / KnowledgeBaseCreate）
- POST/GET /api/v1/knowledge-bases 端点（201 创建 + 列表）
- 前端 /knowledge-bases 管理页面（创建表单 + 列表展示 + 学科/学段配置）
- 聊天输入区添加知识库选择器，WebSocket 消息携带 kb_id
- 确认 chat.db / kb.db 分离方案合理，统一连接生命周期管理
- 添加 data/ 到 .gitignore，清理运行时 SQLite 残留

## B. 代码变更

| 文件 | +行 | -行 | 说明 |
|------|-----|-----|------|
| frontend/src/routes/knowledge-bases.tsx | +203 | — | KB 管理页面 |
| question_agent/kb/database.py | +119 | — | aiosqlite CRUD + asyncio.Lock |
| question_agent/main.py | +128 | -2 | KB router 注册 + lifespan 集成 |
| frontend/src/routes/chat.tsx | +134 | -3 | KB 选择器 + kb_id 发送 |
| tests/test_edge_kb_database.py | +96 | — | 数据库层边缘测试 |
| tests/test_edge_kb_api.py | +81 | — | API 层边缘测试 |
| tests/test_kb_api.py | +66 | — | API 功能测试 |
| question_agent/kb/models.py | +27 | — | Pydantic 模型 |
| question_agent/kb/router.py | +27 | — | FastAPI 路由 |

架构变化：新增 `question_agent/kb/` 模块（独立于 knowledge/），采用 asyncio.Lock 保护单例 aiosqlite 连接。前端新增独立路由页面 + 聊天集成。

## C. 文档现状

| 文档 | 路径 | 状态 |
|------|------|------|
| Spec | specs/2026-04-29-ai-question-agent.md | needs-update — 未反映知识库管理完整功能树 |
| Roadmap | plans/2026-04-29-ai-question-agent.md | confirmed — 知识库创建已标 [x] |
| Toolchain | .harness/ai-question-agent-toolchain.md | needs-update — 未列 aiosqlite 依赖 |
| Items (知识库创建) | items/2026-05-12-09-知识库创建.md | confirmed — F-1~F-6 全部完成 |

## D. 遗留问题

- 知识库列表与删除：roadmap 下一个 [ ] 节点，当前仅有创建和列表，无删除/编辑
- 文档上传到知识库：知识库创建完成但尚无文档关联功能，kb_id 在聊天中传递但后端未使用
- aiosqlite 单例连接：并发安全由 asyncio.Lock 保证，但未测试高并发场景（Phase 1 单机无并发需求）
- Pydantic min_length 不做 strip：空白名 "   " 通过校验，是否需要 strip 预处理待定

## E. 外部知识

- aiosqlite 在 Python 3.12+ 中 asyncio.Lock 单例模式是社区推荐做法，替代 aiosqlite.connect() 上下文管理器的反复开关
- FastAPI 201 + Location header 是 RESTful 资源创建的标准模式，shadcn/ui 的表单模式与 TanStack Router 无冲突

## F. 下一轮建议

1. 优先实现"知识库列表与删除"，因为知识库管理页面缺少删除功能是不完整的 CRUD 体验
2. "文档上传到知识库"优先级次之——已有 /extract 端点和上传 UI，需要关联知识库 ID 并持久化文档记录
3. 考虑在 KB API 中添加 name strip 预处理，避免空白名入库

## G. 量化统计

| 指标 | 值 |
|------|-----|
| Commits | 7 |
| Files changed | 16 |
| Lines added | 931 |
| Lines deleted | 31 |
| Test pass rate | 480/480 (100%) |
| New tests | 27 (KB 相关) |

## H. 架构快照

```mermaid
graph LR
    subgraph Frontend
        KBPage[知识库管理页]
        ChatPage[聊天页面]
        KBSelect[KB 选择器]
    end
    subgraph Backend
        KBRouter[/api/v1/knowledge-bases]:::new
        KBDB[(kb.db aiosqlite)]:::new
        ChatWS[/chat WebSocket]
        ChatDB[(chat.db LangGraph)]
    end
    KBPage -->|POST/GET| KBRouter
    ChatPage -->|WS + kb_id| ChatWS
    KBSelect -->|GET list| KBRouter
    KBRouter --> KBDB
    ChatWS --> ChatDB
    classDef new fill:#90EE90,stroke:#333
```

新增节点标绿。kb.db 独立于 chat.db，业务表与 LangGraph checkpoint 分离。

## J. 关键决策

1. **决策：chat.db 与 kb.db 分离存储** / 原因：LangGraph checkpoint 格式与业务表不兼容，合并会增加耦合 / 后果：两个独立连接管理，需分别处理生命周期
2. **决策：asyncio.Lock 保护 aiosqlite 单例** / 原因：aiosqlite 连接非线程安全，并发创建时可能重复初始化 / 后果：所有 DB 操作经同一连接串行化，Phase 1 足够

## K. 经验教训

- ✅ Pydantic min_length 校验不做 strip — "   " 长度为 3 通过 min_length=1，测试预期需与实际行为一致
- ✅ 前端原型优先（F-3）再增强（F-4 学科/学段）— 避免一步到位的过度设计
- ⚠️ aiosqlite 需显式 close_db — FastAPI lifespan shutdown 必须调用，否则测试残留连接
