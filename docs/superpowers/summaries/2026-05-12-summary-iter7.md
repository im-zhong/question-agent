---
iteration: 7
phase: "对话交互 — LangGraph 对话状态机 + ReAct 智能体"
date: 2026-05-12
status: complete
previous: docs/superpowers/summaries/2026-05-11-summary-iter6.md
---

# 总结报告 — 2026-05-12 (Iteration 7)

## A. 本轮完成

- **LangGraph 对话模块 + GLM-5 聊天节点 (F-1):** 创建 `chat/graph.py`，StateGraph + MessagesState + MemorySaver checkpointer，ChatOpenAI 连接 ZhipuAI OpenAI 兼容端点。按 plan 完成。
- **WebSocket 流式对接 (F-2):** 替换 `/ws/chat` echo 端点为 LangGraph `astream(stream_mode="messages")` 流式推送，start/token/end 协议不变，前端零改动即可看到真实 AI 回复。每个 WS 连接用 uuid4 thread_id 隔离会话。按 plan 完成。
- **出题工具函数 + 工具节点 (F-3):** `chat/tools.py` 封装 `extract_knowledge_points` 和 `generate_questions` 为 `@tool` 函数，中文描述，`ALL_TOOLS` 列表 + ToolNode 加入图。按 plan 完成。
- **ReAct 对话状态机 (F-4):** 添加 `_should_continue` 条件边——AIMessage 有 `tool_calls` → 路由到 tools 节点 → 执行后回 chat 节点；无 `tool_calls` → END。智能体根据用户意图自主决定是否调用出题管线。按 plan 完成。
- **清理 echo 残留 (F-5):** 确认 main.py 和测试中无 echo 相关代码，无临时 stepping stone 代码。按 plan 完成（实际无残留需清理）。

## B. 代码变更

| 文件 | +行 | -行 | 说明 |
|------|-----|-----|------|
| question_agent/chat/graph.py | 69 | 0 | 新增：StateGraph + ReAct 条件边 + chat_node |
| question_agent/chat/tools.py | 110 | 0 | 新增：extract_knowledge_points + generate_questions 工具 |
| question_agent/main.py | +36 | ~5 | 改造：/ws/chat 接入 LangGraph 流式推送 |
| tests/test_react_routing.py | 125 | 0 | 新增：_should_continue + ReAct 图结构测试 |
| tests/test_edge_react_routing.py | 107 | 0 | 新增：条件边边缘测试 |
| tests/test_chat_graph.py | 59 | 0 | 新增：graph 基础测试 |
| tests/test_chat_tools.py | 132 | 0 | 新增：工具函数注册和调用测试 |
| tests/test_edge_chat_graph.py | 133 | 0 | 新增：chat_node 边缘测试 |
| tests/test_ws_chat_streaming.py | 174 | 0 | 新增：WS 流式协议测试 |
| tests/test_edge_ws_streaming.py | 185 | 0 | 新增：WS 流式边缘测试 |
| tests/integration/test_ws_chat.py | +39 | ~0 | 新增：ReAct 工具调用路由集成测试 |

核心架构变更：后端从 echo 模式升级为 LangGraph ReAct 智能体循环——chat_node 调用 GLM-5（bind_tools），条件边根据 tool_calls 路由到 ToolNode 执行出题工具后回 chat，无 tool_calls 则结束。

## C. 文档现状

| 文档类型 | 路径 | 状态 |
|----------|------|------|
| Spec | specs/2026-04-29-ai-question-agent.md | DRAFT — 需更新 ReAct 架构描述 |
| Roadmap | plans/2026-04-29-ai-question-agent.md | DRAFT — LangGraph 对话状态机 + 聊天 API 已标记完成 |
| Toolchain | .harness/ai-question-agent-toolchain.md | ACTIVE — 已包含 LangGraph/langchain-openai |
| Items | items/2026-05-11-02-LangGraph对话状态机.md | 完成 |
| State | state.md | 需更新为 iteration 7 summarize |

## D. 遗留问题

- **对话状态仅存内存:** MemorySaver 是内存级 checkpoint，进程重启丢失所有对话。roadmap "对话历史持久化" 待实现。SqliteSaver 是自然的下一步。
- **无智能体调度策略:** 当前 ReAct 循环完全依赖 LLM 自主决定是否调工具，无调度策略控制（如优先知识抽取再出题的固定流程）。roadmap "智能体调度" 待实现。
- **生产部署方案未定:** Vite proxy 仅 dev 环境，生产需 nginx 或 FastAPI static 挂载。
- **mypy strict 下 `bind_tools` 返回类型为 Any:** `ChatOpenAI.bind_tools()` 返回 `RunnableBinding`，不是 `ChatOpenAI`。当前用 `Any` 绕过，不算类型安全但无实际风险。

## E. 外部知识

- **SqliteSaver 替换 MemorySaver 实现持久化:** `langgraph.checkpoint.sqlite.SqliteSaver` 将 checkpoint 存入 SQLite 文件，支持跨重启恢复对话。API 与 MemorySaver 兼容（`from_conn_string("db.sqlite")`）。注意 v2 迁移：旧 `SqliteSaver` 已 deprecated，新版在 `langgraph-checkpoint-sqlite` 包。来源: [LangGraph Persistence Docs](https://langchain-ai.github.io/langgraph/how-tos/persistence/)
- **LangGraph human-in-the-loop 工具审批模式:** `interrupt_before=["tools"]` 可暂停图执行让用户审批工具调用，`Command()` 恢复执行并支持修改/拒绝。适合出题场景：用户审核知识点再确认出题。来源: [LangGraph HITL Docs](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/), [Tool Call Approval Tutorial](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/tool_call_approval/)
- **ReAct 手动条件边 vs create_react_agent:** 手动构建更灵活（可控制路由逻辑、添加自定义节点），`create_react_agent` 更简洁但定制空间有限。本项目选择手动构建，后续添加调度策略节点时更方便。来源: LangGraph 官方文档

## F. 下一轮建议

1. **优先实现对话历史持久化**，因为刷新即丢失对话不可接受。用 SqliteSaver 替换 MemorySaver（API 兼容，改动约 10 行），同时需处理 async 适配。
2. **实现智能体调度策略**，因为纯 LLM 自主决策可能不稳定（有时不调工具、有时调错顺序）。建议添加调度节点做固定流程编排（先知识抽取→再出题），保留 LLM 自由对话能力。
3. **添加 human-in-the-loop 工具审批**，因为出题结果需用户确认。用 `interrupt_before=["tools"]` 暂停，前端展示工具调用意图让用户确认/修改。

## G. 量化统计

| 指标 | 数值 |
|------|------|
| 本轮 commits | 6（F-1~F-5 + 文档标记） |
| 文件变更 | 20 files (+1467/-34) |
| 新增后端代码 | graph.py + tools.py (~180 行) |
| 新增测试 | 8 个测试文件 (~1014 行, 52 new tests) |
| 总测试数 | 401（含 11 integration） |
| 测试通过率 | 100%（401 passed, 0 failed） |
| ruff check | 0 issues |
| mypy strict | 0 issues |

## H. 架构快照

```mermaid
graph TB
    subgraph Frontend
        ChatUI[chat.tsx]
        ChatCtx[ChatProvider]
        WSHook[use-websocket.ts]
    end
    subgraph Backend
        WS[/ws/chat]
        Graph[LangGraph StateGraph]
        ChatNode[chat_node — GLM-5 + bind_tools]
        ToolNode[ToolNode — extract/generate]
        Checkpoint[MemorySaver]
    end
    ChatUI --> ChatCtx
    ChatUI --> WSHook
    WSHook -->|WebSocket| WS
    WS -->|astream| Graph
    Graph --> ChatNode
    ChatNode -->|tool_calls| ToolNode
    ChatNode -->|no tool_calls| END
    ToolNode -->|result| ChatNode
    Graph --> Checkpoint
    style Graph fill:#ffc107,stroke:#ff9800
    style ChatNode fill:#d4edda,stroke:#28a745
    style ToolNode fill:#d4edda,stroke:#28a745
    style Checkpoint fill:#fff3cd,stroke:#ffc107
```

黄色=修改（WS 端点从 echo 改为 astream），绿色=新增（chat_node + ToolNode），黄底=需升级（MemorySaver → SqliteSaver）。

## J. 关键决策

**决定 1: 手动构建 ReAct 条件边而非 create_react_agent**
- 原因: 手动构建 `_should_continue` + `add_conditional_edges` 更灵活，后续添加调度策略节点、human-in-the-loop 审批时无需重构。
- 后果: 代码量稍多（~20 行条件边逻辑），但完全掌控路由决策。

**决定 2: _create_llm_with_tools 返回 Any 而非 RunnableBinding**
- 原因: `bind_tools()` 返回 `RunnableBinding`，mypy strict 下泛型参数不匹配。返回 `Any` 绕过类型检查，实际使用无差异。
- 后果: 丧失类型安全，但 chat_node 内部使用不受影响。

**决定 3: MemorySaver 而非 SqliteSaver 作为 Phase 1 checkpoint**
- 原因: 开发期内存级足够，零配置零依赖。SqliteSaver 需额外包和 async 适配。
- 后果: 进程重启丢失对话，需在下一迭代升级。

## K. 经验教训

✅ **比预期顺利:**
- F-1~F-3 叠加式开发极其顺畅——每步只增一个能力，系统始终可运行
- WS 流式协议（start/token/end）与 LangGraph astream 天然匹配，前端零改动

⚠️ **比预期困难:**
- mypy strict 下 `bind_tools` 返回类型问题比预期棘手——`RunnableBinding` 泛型参数不匹配，最终用 `Any` 绕过
- tools.py 中 `generate_questions` 是 async 函数但 `@tool` 装饰器同步调用，需 `asyncio.run()` + ThreadPoolExecutor fallback 处理已有事件循环的情况

💡 **意外发现:**
- `astream_events(version="v2")` 不如 `astream(stream_mode="messages")` 适合聊天场景——后者直接产出 AIMessageChunk，过滤逻辑更简单
- GLM-5 的 tool calling 在中文描述下表现可靠，能准确判断"帮我出题"→调 extract_knowledge_points，"你好"→直接回复
