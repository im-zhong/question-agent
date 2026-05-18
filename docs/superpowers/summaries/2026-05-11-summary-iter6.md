---
iteration: 6
phase: "对话交互 — ChatGPT 风格聊天界面"
date: 2026-05-11
status: complete
previous: docs/superpowers/summaries/2026-05-02-summary-iter4.md
---

# 总结报告 — 2026-05-11 (Iteration 6)

## A. 本轮完成

- **前端从 Next.js 迁移到 Vite + TanStack Router (F-0):** 删除 Next.js 配置（next.config.ts/postcss.config.mjs/globals.css），改用 Vite 构建 + TanStack Router 文件路由 + Tailwind v4 Vite 插件。偏差：plan 未包含此迁移，但因 Next.js 与聊天 SPA 不匹配而必须执行。
- **聊天页面布局骨架 (F-1):** ChatGPT 风格双栏布局 — 可折叠侧边栏（对话列表+新建按钮）+ 右侧聊天主区域。按 plan 完成。
- **消息气泡与输入交互 (F-2):** 用户/助手消息气泡（左右对齐）+ Markdown 渲染 + Enter 发送 / Shift+Enter 换行。初始用 mock 回复验证布局。按 plan 完成。
- **WebSocket 端到端通信原型 (F-3):** 后端 `/ws/chat` 流式 echo 端点（start/token/end 协议）+ 前端 `useWebSocket` hook + 连接状态显示。按 plan 完成。
- **对话会话管理 (F-4):** React Context (ChatProvider) 管理对话列表/活跃对话/消息，新建/切换对话互不干扰，首条用户消息自动设为对话标题。按 plan 完成。
- **流式响应展示 (F-5):** token-by-token 逐字渲染 + 流式光标动画 + 自动滚动 + typing indicator。按 plan 完成。
- **Mock 清理与样式打磨 (F-6):** 确认无 mock 残留，添加断线重连按钮，侧边栏改为暗色 zinc 主题，输入框圆角阴影，空状态居中提示。按 plan 完成。
- **WebSocket 代理修复 (post-F-6):** Vite 添加 `/ws` 代理 + 前端 WS_URL 改为动态拼接 `window.location.host`，解决开发环境跨域连接问题。偏差：plan 未包含，实测发现。

## B. 代码变更

| 文件 | +行 | -行 | 说明 |
|------|-----|-----|------|
| frontend/src/routes/chat.tsx | 192 | 0 | 新增：聊天主页面（消息/输入/连接状态/重连） |
| frontend/src/lib/chat-context.tsx | 115 | 0 | 新增：对话状态管理（ChatProvider/useChat） |
| frontend/src/hooks/use-websocket.ts | 67 | 0 | 新增：WebSocket 连接管理 hook |
| frontend/src/components/chat-sidebar.tsx | 46 | 0 | 新增：侧边栏组件（暗色主题） |
| frontend/src/routes/__root.tsx | +49 | ~30 | 改造：ChatProvider 包裹 + 侧边栏布局 |
| question_agent/main.py | +21 | ~5 | 新增：/ws/chat WebSocket echo 端点 |
| tests/test_edge_chat_layout.py | 172 | 0 | 新增：聊天布局/可访问性/WS 协议测试 |
| frontend/vite.config.ts | +5 | 0 | 新增：/ws WebSocket 代理 |

核心架构变更：前端新增聊天层（chat-route + chat-context + use-websocket + chat-sidebar），后端新增 `/ws/chat` WebSocket 端点。前端通过 `start/token/end` 协议实现流式渲染，ChatProvider 统一管理对话状态。

## C. 文档现状

| 文档类型 | 路径 | 状态 |
|----------|------|------|
| Spec | specs/2026-04-29-ai-question-agent.md | DRAFT — 已更新对话交互架构图和功能层级 |
| Roadmap | plans/2026-04-29-ai-question-agent.md | DRAFT — 聊天界面标记完成 |
| Toolchain | .harness/ai-question-agent-toolchain.md | ACTIVE — 已添加 LangGraph/Vite/shadcn 条目 |
| Items | items/2026-05-11-01-聊天界面.md | 完成 |
| State | state.md | 需更新为 iteration 6 summarize |

## D. 遗留问题

- **WebSocket 代理修复未提交:** vite.config.ts 和 chat.tsx 的 WS 代理改动尚未 commit（用户中断了 dev-loop）。
- **后端仍是 echo 模式:** `/ws/chat` 仅回显用户消息，未接入 LangGraph 或真实出题管线。roadmap 中"LangGraph 对话状态机"和"智能体调度"为下一步。
- **对话状态仅存内存:** ChatProvider 用 React state 管理，刷新页面丢失所有对话。roadmap 中"对话历史持久化"待实现。
- **前端 WS_URL 在生产环境未验证:** 动态拼接 `window.location.host` 在 dev 模式下走 Vite 代理，但生产环境需 nginx 反向代理配合。
- **Vite proxy 仅开发环境生效:** toolchain 风险已记录。生产部署方案待定。

## E. 外部知识

- **LangGraph + FastAPI WebSocket 集成模式:** 用 `astream_events(version="v2")` 逐 token 推送，过滤 `on_chat_model_stream` 事件类型，`thread_id` 在 config 中传递做会话隔离。来源: LangGraph 官方文档
- **LangGraph ReAct Agent 模式:** `create_react_agent(llm, tools)` 预建 ReAct 状态机，自动处理 think→act→observe 循环和 tool_calls 条件路由。适合出题场景：用户消息→调度知识抽取/出题工具→流式返回。来源: LangGraph 官方文档
- **WebSocket 连接管理最佳实践:** 断线重连用指数退避 + ping/pong keepalive，大对话状态需 pruning 防止 checkpoint 膨胀。来源: FastAPI WebSocket 文档, LangGraph 文档

## F. 下一轮建议

1. **优先实现 LangGraph 对话状态机**，因为当前后端 `/ws/chat` 是纯 echo，无法做任何智能交互。用 `create_react_agent` + 出题工具函数（extract_knowledge, generate_questions）替换 echo 逻辑，让对话能真正调度出题管线。
2. **对话历史持久化**紧随其后，因为内存态对话刷新即丢失，用户体验不可接受。建议用 LangGraph 的 MemorySaver 或 SqliteSaver。
3. **生产部署方案需确定**，因为 Vite proxy 仅 dev 生效。建议将前端静态文件挂载到 FastAPI static 目录同源提供，或配置 nginx 反向代理。
4. **WebSocket 代理修复需先提交**，当前改动未 commit。

## G. 量化统计

| 指标 | 数值 |
|------|------|
| 本轮 commits | 8（含 F-0 迁移 + F-1~F-6 + 文档标记） |
| 文件变更 | 19 files (+2987/-719) |
| 新增前端代码 | chat.tsx + chat-context.tsx + use-websocket.ts + chat-sidebar.tsx (~420 行) |
| 新增后端代码 | /ws/chat 端点 (~21 行) |
| 新增测试 | test_edge_chat_layout.py (~172 行, 33 tests) |
| 总测试数 | 337（含 5 新增 F-6 测试） |
| 测试通过率 | 100%（337 passed, 0 failed） |
| ruff check | 0 issues |
| mypy strict | 0 issues |

## H. 架构快照

```mermaid
graph TB
    subgraph Frontend
        ChatUI[chat.tsx — 消息/输入/连接状态]
        Sidebar[chat-sidebar.tsx — 暗色侧边栏]
        ChatCtx[chat-context.tsx — ChatProvider]
        WSHook[use-websocket.ts — WS 管理]
    end
    subgraph Backend
        WS[/ws/chat — echo 端点]
        Health[/health]
        Extract[/extract]
        Knowledge[/knowledge]
        QGen[/questions/generate]
    end
    ChatUI --> ChatCtx
    ChatUI --> WSHook
    WSHook -->|WebSocket| WS
    WS -.->|echo only| ChatUI
    Sidebar --> ChatCtx
    style WSHook fill:#d4edda,stroke:#28a745
    style WS fill:#d4edda,stroke:#28a745
    style ChatCtx fill:#d4edda,stroke:#28a745
    style ChatUI fill:#d4edda,stroke:#28a745
    style Sidebar fill:#d4edda,stroke:#28a745
```

本轮新增全部前端聊天层 + 后端 WebSocket echo 端点（绿色）。虚线表示 `/ws/chat` 当前仅 echo，待接入 LangGraph 后将实线连接到出题管线。

## J. 关键决策

**决定 1: WebSocket 而非 SSE 作为聊天通信协议**
- 原因: 用户明确要求使用 WebSocket。双向通信能力更适合对话交互（用户可随时发消息/中断），SSE 仅单向推送。
- 后果: 前端需管理连接状态（connect/disconnect/reconnect），比 SSE 复杂但交互能力更强。

**决定 2: 前端从 Next.js 迁移到 Vite + TanStack Router**
- 原因: Next.js SSR 模式与纯 SPA 聊天应用不匹配。Vite 构建更快、HMR 即时，TanStack Router 类型安全路由适合 SPA。
- 后果: 删除 next.config.ts/postcss.config.mjs/globals.css 等文件，增加 vite.config.ts。路由从文件系统约定改为 TanStack Router 文件路由。

**决定 3: ChatProvider Context 而非 URL 参数管理对话状态**
- 原因: 对话数据是全局 UI 状态（侧边栏和聊天页共享），URL 参数不适合存储消息列表。
- 后果: 刷新丢失对话（内存态），需后续持久化层替换。但当前阶段验证交互流程足够。

## K. 经验教训

✅ **比预期顺利:**
- F-1~F-5 的逐步叠加极其顺畅 — 每一步在前一步基础上只增加一个能力，系统始终可运行
- start/token/end 流式协议设计简洁，前后端对接一次通过

⚠️ **比预期困难:**
- Next.js → Vite 迁移比预期多花时间 — 不仅是配置替换，还涉及路由模式、CSS 方案、构建工具全面更换
- WebSocket 开发环境跨域问题在本地测试时不易发现（后端直连可以，但浏览器通过 Vite dev server 连接有问题），需要添加 Vite WS 代理

💡 **意外发现:**
- `createMessageId()` 封装比导出可变 `let` 变量更可靠 — TypeScript 对跨模块可变变量导入行为不一致，函数封装无此问题
- Vite 的 WebSocket 代理 (`ws: true`) 需要显式配置，不像 HTTP 代理那样自动生效
