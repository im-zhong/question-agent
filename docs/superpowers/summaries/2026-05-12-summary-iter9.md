---
iteration: 9
phase: "前端展示 + 导出 + 主观题"
date: 2026-05-12
status: complete
previous: docs/superpowers/summaries/2026-05-12-summary-iter8.md
---

# 总结报告 — 2026-05-12 (Iteration 9)

## A. 本轮完成

- **知识点列表展示 (F-1~F-5):** WS 流式端点拦截 ToolMessage 发送 type=data 消息，前端 KnowledgePointCard/QuestionsList 卡片组件，消息气泡检测 structuredData 渲染对应卡片。按 plan 完成。
- **题目预览展示 (F-1~F-3):** QuestionCard 增加正确答案绿色高亮+CheckCircle2 图标、难度徽章（基础/中等/提高）颜色区分，上传页面同步适配。按 plan 完成。
- **题目导出 (F-1~F-3):** POST /questions/export 端点接受 questions 数组+format 参数，返回 Markdown 文件（Content-Disposition 附件头），上传页面添加"导出 Markdown"按钮。按 plan 完成。
- **主观题生成 (F-1~F-6):** QuestionType 新增 short_answer/essay，新增 _SHORT_ANSWER_PROMPT 和 _ESSAY_PROMPT 含 reference_answer schema，前端主观题卡片无选项+参考答案折叠区。按 plan 完成。

## B. 代码变更

| 文件 | +行 | -行 | 说明 |
|------|-----|-----|------|
| question_agent/chat/graph.py | +131 | ~3 | WS data 消息拦截 + question_type 调度 |
| question_agent/main.py | +123 | ~10 | /questions/export 端点 + question_type 参数 |
| question_agent/questions/prompts.py | +126 | ~20 | 主观题 prompt 模板 (short_answer + essay) |
| question_agent/questions/llm.py | +47 | ~5 | question_type 参数 + reference_answer 支持 |
| question_agent/questions/models.py | +15 | ~1 | QuestionType 扩展 + reference_answer 字段 |
| question_agent/questions/generator.py | +36 | ~2 | question_type 透传 |
| frontend/src/lib/chat-context.tsx | +109 | ~10 | StructuredData 类型 + localStorage 持久化 + addStructuredData |
| frontend/src/routes/chat.tsx | +92 | ~5 | WS data 消息处理 + structuredData 渲染 |
| frontend/src/routes/upload.tsx | +138 | ~5 | 题目卡片正确答案/难度 + 导出按钮 |
| tests/test_ws_chat_streaming.py | +194 | ~5 | data 消息测试扩展 |

核心架构变更：ToolMessage 结构化数据通过 WS type=data 消息传递到前端，实现聊天中工具结果的可视化渲染。主观题扩展了出题管线的题型覆盖范围。

## C. 文档现状

| 文档类型 | 路径 | 状态 |
|----------|------|------|
| Spec | specs/2026-04-29-ai-question-agent.md | DRAFT — 需更新主观题题型 |
| Roadmap | plans/2026-04-29-ai-question-agent.md | DRAFT — 4 项标记完成 |
| Toolchain | .harness/ai-question-agent-toolchain.md | ACTIVE — 需新增导出/主观题记录 |
| Items | items/2026-05-12-05~08-*.md | 完成 |
| State | state.md | 需更新为 iteration 9 |

## D. 遗留问题

- **所有变更均未提交:** 工作目录有 25 文件 +1101/-196 行变更未 commit
- **知识点选择与出题触发未实现:** 聊天中可浏览知识点列表，但点击知识点触发出题的交互未实现
- **导出格式仅 Markdown:** 缺少 Word/LaTeX 等格式，roadmap 列了"多格式批量导出"
- **前端难度选择 UI 未实现:** API 支持难度参数，聊天界面无难度选择入口
- **主观题 dispatch 意图检测粗糙:** "出简答题" 等关键词匹配，长尾表达可能漏判
- **生产部署方案未定:** Vite proxy 仅 dev，生产需 nginx 或 FastAPI static 挂载

## E. 外部知识

- **SSE vs WebSocket 选型:** 2024-2025 趋势是纯服务端推送用 SSE（更简单、自动重连），需要客户端交互（取消/工具审批）用 WebSocket。本项目 WebSocket 选型合理——用户可能中途取消出题。来源: FastAPI 社区最佳实践
- **Bloom's Taxonomy 认知层级引导难度:** 仅 prompt 标注难度等级效果有限，结合 Remember→Understand→Apply→Analyze→Evaluate→Create 认知层级可提升难度控制可靠性。来源: AAAI 2025, arXiv 2025
- **LLM 出题的参考答案可靠性:** 学术共识"先推理再生成答案"——CoT prompting + 独立验证调用可降低答案幻觉率。本项目当前方案直接生成 reference_answer，后续可增加反向验证步骤。来源: EDM 2025

## F. 下一轮建议

1. **优先提交当前变更**，因为 25 文件 +1100 行未提交代码风险高，一次意外可能导致大量工作丢失。建议按功能拆为 4-5 个原子 commit。
2. **实现知识点选择与出题触发**，因为已有知识点列表卡片展示，但缺少用户交互闭环——点击知识点触发出题是"教材→知识点→题目"端到端 demo 的最后缺口。
3. **添加前端难度选择 UI**，因为后端 API 已支持 difficulty 参数但用户无法在聊天中选择，添加下拉或快捷按钮即可闭环。
4. **考虑引入 Bloom's Taxonomy 认知层级** 替代/增强 basic/intermediate/advanced 难度标签，学术研究表明后者对 LLM 出题难度控制效果不稳定。

## G. 量化统计

| 指标 | 数值 |
|------|------|
| 本轮功能点 | 4（知识点展示/题目预览/导出/主观题） |
| 文件变更 | 25 files (+1101/-196) |
| 新增后端代码 | graph.py + main.py + prompts.py + llm.py ~340 行 |
| 新增前端代码 | chat-context.tsx + chat.tsx + upload.tsx ~340 行 |
| 新增测试 | ~200 行 (WS data 消息 + 主观题 14 个) |
| 总测试数 | 432+（含 integration） |
| commits | 0（全部变更未提交） |

## H. 架构快照

```mermaid
graph TB
    subgraph Frontend
        ChatUI[chat.tsx]
        ChatCtx[ChatProvider — localStorage + StructuredData]
        Cards[chat-cards.tsx — KnowledgePoint + Question + Subjective]
        Upload[upload.tsx — 题目卡片 + 导出按钮]
    end
    subgraph Backend
        WS[/ws/chat — conversation_id]
        Dispatch[dispatch_node — 意图分类]
        ChatNode[chat_node — GLM-5 + bind_tools]
        ToolNode[ToolNode — extract/generate]
        Export[/questions/export — Markdown]
    end
    ChatUI --> ChatCtx
    ChatUI -->|WS data 消息| Cards
    Upload -->|download| Export
    WS -->|astream + type=data| Dispatch
    Dispatch -->|extract/generate| ToolNode
    Dispatch -->|chat| ChatNode
    ChatNode -->|tool_calls| ToolNode
    ChatNode -->|no tool_calls| END
    ToolNode -->|result| ChatNode
    style Cards fill:#d4edda,stroke:#28a745
    style Export fill:#d4edda,stroke:#28a745
    style Dispatch fill:#fff3cd,stroke:#ffc107
```

绿色=新增（chat-cards 组件 + 导出端点），黄色=修改（dispatch_node 新增 question_type 意图检测）。

## J. 关键决策

**决定 1: ToolMessage 拦截 + WS type=data 消息传递结构化数据**
- 原因: LangGraph ToolNode 的结果存在 ToolMessage 中，前端无法直接访问。通过在 WS 流中拦截 ToolMessage 并发送 type=data 消息，前端可解析为卡片组件。
- 后果: data 消息与 token 消息分离，前端需同时处理两种流式消息类型，复杂度略增但渲染更灵活。

**决定 2: question_type 优先级高于 tags 类别**
- 原因: 用户说"出简答题"时，题型意图比知识点类别（concept/formula 等）更明确。select_prompt 中 question_type 参数优先匹配。
- 后果: 同时指定 question_type 和 tags 时，question_type 决定 prompt 模板，tags 作为内容约束。

**决定 3: 主观题 reference_answer 必填而非可选**
- 原因: 主观题的核心价值在于参考答案，无参考答案的主观题无教学意义。
- 后果: 主观题生成时 LLM 必须返回 reference_answer，否则校验失败；选择题的 correct_answer 可选（向后兼容）。

## K. 经验教训

✅ **比预期顺利:**
- chat-cards 组件复用性好——KnowledgePointCard 和 QuestionCard 独立渲染，消息气泡只需检测 structuredData 类型分发
- 导出端点极简——Markdown 格式化用 f-string 拼接即可，不需要 Jinja2 模板

⚠️ **比预期困难:**
- WS 流中 ToolMessage 拦截位置需仔细选择——太早拿不到完整结果，太晚无法与 token 流同步
- 主观题 prompt 模板设计比选择题更复杂——reference_answer 需要完整的推理步骤而非单一选项

💡 **意外发现:**
- StructuredData 类型只需 tool + content 两个字段即可区分所有卡片类型——无需为每种工具定义不同的数据结构
- crypto.randomUUID() 在 localStorage 持久化场景下比自增 ID 更可靠——避免跨标签页 ID 冲突
