---
iteration: 8
phase: "对话后端完善 + 正确答案 + 难度等级控制"
date: 2026-05-12
status: complete
previous: docs/superpowers/summaries/2026-05-12-summary-iter7.md
---

# 总结报告 — 2026-05-12 (Iteration 8)

## A. 本轮完成

- **对话历史持久化 (F-1~F-5):** 用 SqliteSaver 替换 MemorySaver，conversation_id 通过 WS query param 传递，断线重连后服务端发送 history 消息恢复上下文，前端 localStorage 持久化会话元数据。按 plan 完成。
- **智能体调度 (F-1~F-5):** 添加 dispatch_node 意图分类（extract/generate/chat），extract 和 generate 意图强制构造 synthetic AIMessage + tool_calls 路由到 ToolNode，chat 意图直接到 chat_node 自由对话。按 plan 完成。
- **正确答案生成:** 所有 6 个类别 prompt 添加 correct_answer 字段到 JSON schema 和示例，QuestionStem 模型新增 correct_answer 字段，generate_questions 工具输出包含正确答案。按 plan 完成。
- **难度等级控制:** QuestionStem 新增 DifficultyLevel 类型 + difficulty 字段，generate_question_llm 根据难度参数追加 DIFFICULTY_INSTRUCTIONS 到 system prompt，API 端点暴露 difficulty 查询参数。按 plan 完成。

## B. 代码变更

| 文件 | +行 | -行 | 说明 |
|------|-----|-----|------|
| question_agent/chat/graph.py | +117 | ~3 | dispatch_node + _route_after_dispatch + SqliteSaver + conversation_id |
| question_agent/chat/intent.py | 30 | 0 | 新增：classify_intent 意图分类 |
| question_agent/chat/tools.py | +1 | 0 | 添加 correct_answer + difficulty 到 generate 输出 |
| question_agent/main.py | +46 | ~10 | WS conversation_id + history 重发 + difficulty 参数 |
| question_agent/questions/llm.py | +31 | ~5 | _DIFFICULTY_INSTRUCTIONS + difficulty 参数注入 |
| question_agent/questions/models.py | +4 | 0 | DifficultyLevel + correct_answer + difficulty 字段 |
| question_agent/questions/prompts.py | +29 | ~20 | 6 个 prompt 添加 correct_answer schema |
| frontend/src/lib/chat-context.tsx | +82 | ~10 | UUID conversation_id + localStorage 持久化 |
| frontend/src/routes/chat.tsx | +32 | ~5 | WS URL 带 conversation_id + history 消息处理 |
| tests/test_difficulty_level.py | 130 | 0 | 新增：9 个难度控制测试 |
| tests/test_correct_answer.py | 109 | 0 | 新增：8 个正确答案测试 |
| tests/test_dispatch.py | ~200 | 0 | 新增：16 个调度节点测试 |

核心架构变更：从纯 ReAct（LLM 自主决策是否调工具）升级为 dispatch→conditional→tools/chat 的受控调度。SqliteSaver 替代 MemorySaver 实现持久化。

## C. 文档现状

| 文档类型 | 路径 | 状态 |
|----------|------|------|
| Spec | specs/2026-04-29-ai-question-agent.md | DRAFT — Unknowns 已追加调度/触发词/HITL 决策点 |
| Roadmap | plans/2026-04-29-ai-question-agent.md | DRAFT — 4 项标记完成并链接 items |
| Toolchain | .harness/ai-question-agent-toolchain.md | ACTIVE — 新增 SqliteSaver/dispatch 调研记录 |
| Items | items/2026-05-12-01~04-*.md | 完成 — 对话持久化/调度/正确答案/难度控制 |
| State | state.md | 需更新为 iteration 8 summarize |

## D. 遗留问题

- **客观题生成（选择题）已在实现中但 roadmap 未勾选:** 所有题目当前都是选择题，应标记为完成
- **前端难度选择 UI 未实现:** API 支持难度参数，但聊天界面无难度选择入口
- **conversation_id 跨标签页隔离不足:** localStorage 共享导致同一浏览器多标签页可能复用会话
- **SqliteSaver 线程安全:** `check_same_thread=False` 在多连接场景下需评估
- **生产部署方案未定:** Vite proxy 仅 dev，生产需 nginx 或 FastAPI static 挂载

## E. 外部知识

- **LLM 难度控制效果有限:** 2025 年多篇论文（arXiv, EDM 2025）指出，仅在 prompt 中标注难度等级（如 "generate a hard question"）不足以可靠控制实际难度。few-shot 示例匹配目标难度 + Bloom's Taxonomy 认知层级分类更有效。本项目当前方案（prompt 追加难度指令）是起点，后续可引入认知层级引导。
- **Bloom's Taxonomy 难度映射:** AAAI 2025 论文提出将认知层级（Remember→Understand→Apply→Analyze→Evaluate→Create）映射到题目难度，比单纯标注 "basic/intermediate/advanced" 更有教学意义。来源: [AAAI 2025](https://aaai.org)
- **知识点浏览 UI 最佳实践:** 树形结构 + 面包屑导航适合层级知识点；列表/网格/图谱三种视图切换；搜索 + 标签筛选组合；选中态明显反馈。参考 Duolingo 技能树、Obsidian 知识图谱。来源: 2025-2026 UI 设计趋势

## F. 下一轮建议

1. **优先实现知识点列表展示**，因为已具备完整知识抽取管线和对话式出题能力，但用户无法在聊天中浏览和选择知识点来触发出题。前端列表组件 + 后端 /knowledge 端点对接即可打通"教材→知识点浏览→选择出题"端到端 demo。
2. **实现题目预览展示**，因为生成题目后用户只能在 WS 消息中看到 JSON，缺少结构化展示（题干、选项、正确答案高亮）。与知识点列表组合可形成完整出题闭环 demo。
3. **考虑引入 Bloom's Taxonomy 认知层级** 替代/增强当前 basic/intermediate/advanced 难度标签，因为学术研究表明后者对 LLM 出题的难度控制效果不稳定。

## G. 量化统计

| 指标 | 数值 |
|------|------|
| 本轮功能点 | 4（对话持久化/智能体调度/正确答案/难度控制） |
| 文件变更 | 21 files (+484/-106, 未含新测试文件) |
| 新增后端代码 | graph.py + intent.py 改造 ~150 行, questions 层 ~60 行 |
| 新增前端代码 | chat-context.tsx + chat.tsx ~120 行 |
| 新增测试 | 3 个测试文件 (~440 行, 33 new tests) |
| 总测试数 | 429（含 integration） |
| 测试通过率 | 100%（429 passed, 0 failed） |
| ruff check | 0 issues |
| mypy strict | 0 issues |

## H. 架构快照

```mermaid
graph TB
    subgraph Frontend
        ChatUI[chat.tsx]
        ChatCtx[ChatProvider — localStorage + UUID]
        WSHook[use-websocket.ts]
    end
    subgraph Backend
        WS[/ws/chat — conversation_id]
        Dispatch[dispatch_node — 意图分类]
        ChatNode[chat_node — GLM-5 + bind_tools]
        ToolNode[ToolNode — extract/generate]
        Checkpoint[SqliteSaver — data/chat.db]
    end
    ChatUI --> ChatCtx
    ChatUI --> WSHook
    WSHook -->|WebSocket + conv_id| WS
    WS -->|astream| Dispatch
    Dispatch -->|extract/generate| ToolNode
    Dispatch -->|chat| ChatNode
    ChatNode -->|tool_calls| ToolNode
    ChatNode -->|no tool_calls| END
    ToolNode -->|result| ChatNode
    Dispatch -.->|history on reconnect| WS
    Checkpoint --- Dispatch
    style Dispatch fill:#d4edda,stroke:#28a745
    style Checkpoint fill:#d4edda,stroke:#28a745
    style ChatNode fill:#fff3cd,stroke:#ffc107
```

绿色=新增（dispatch_node + SqliteSaver），黄色=修改（chat_node 现接收调度路由结果）。

## J. 关键决策

**决定 1: dispatch_node 显式调度替代纯 ReAct 自主决策**
- 原因: 纯 ReAct 模式下 LLM 有时不调工具或调错顺序，对"出题""提取知识点"等明确意图场景不可靠。dispatch_node 通过关键词+文本长度规则分类意图，强制构造 tool_calls。
- 后果: 意图分类基于规则而非语义理解，长尾场景可能误分类；但核心出题流程稳定性大幅提升。

**决定 2: SqliteSaver 直接连接而非 from_conn_string**
- 原因: `SqliteSaver.from_conn_string()` 返回 context manager，`graph.compile(checkpointer=...)` 不接受。直接 `sqlite3.connect()` + `SqliteSaver(conn)` + `setup()` 是可用方案。
- 后果: 需手动管理连接生命周期和 `check_same_thread=False`，但简单直接。

**决定 3: 难度指令追加到 system prompt 末尾而非替换**
- 原因: 类别 prompt（concept/formula 等）已有精心设计的策略和规则，难度指令是补充而非替代。追加方式保持 prompt 结构一致。
- 后果: LLM 可能对追加指令的遵循度低于 prompt 前段内容，后续可考虑将难度融入 prompt 模板。

## K. 经验教训

✅ **比预期顺利:**
- dispatch_node + synthetic AIMessage 方案比预期简洁——只需 ~50 行就实现了稳定的三路调度
- SqliteSaver 替换 MemorySaver 改动极小（~10 行核心代码），API 确实兼容

⚠️ **比预期困难:**
- SqliteSaver.from_conn_string() 返回 context manager 导致 TypeError，排查耗时较长——文档未明确说明返回类型差异
- mypy strict 下 `msg.content` 是 `str | list[str | dict]` 而非 `str`，多个地方需要 `str()` 包装
- 现有 category-aware 测试因 difficulty 指令追加而失败——prompt 拼接改变了 system message 内容，需用 startswith 替代完全匹配

💡 **意外发现:**
- crypto.randomUUID() 在浏览器中生成稳定 UUID，比 Math.random 更适合会话标识
- LLM 难度控制的学术研究表明单纯 prompt 标注效果有限，Bloom's Taxonomy 认知层级引导可能是更优方案
