# 02 - 智能体核心 Workflow

本系统有两条核心处理路径，共享同一套管线模块，但入口和交互方式完全不同。

## 路径 A：REST 文件上传管线

适用于一次性处理：用户上传文件，系统完成全流程，返回结果。

```
用户上传文件 (PDF/DOCX/TXT)
     │
     ▼
┌─────────────────────────────────┐
│  1. 文档解析 (extractors/)       │
│  PDF → pdfplumber                │
│  DOCX → python-docx              │
│  TXT → chardet + utf-8 decode    │
│                                  │
│  输出: paragraphs[]              │
│  每段含: text, font_size,        │
│         is_bold, style_name,     │
│         page_number              │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  2. 章节检测 (chapters/)         │
│                                  │
│  规则检测器 ──→ 高置信度标题      │
│  (编号/样式/字体)                 │
│       +                          │
│  LLM 检测器 ──→ 语义补充         │
│       ↓                          │
│  混合合并器 ──→ 最终标题列表      │
│       ↓                          │
│  章节树构建 ──→ ChapterNode 树   │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  3. 窗口分割 (knowledge/windows) │
│                                  │
│  每个章节文本 → 窗口列表          │
│  窗口: ≤3000 字符                │
│  在段落边界切分                  │
│  保持段落完整性                  │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  4. 知识点提取 (knowledge/)      │
│                                  │
│  对每个窗口:                     │
│    规则检测器 → 标记词匹配       │
│    LLM 检测器  → 语义提取        │
│       ↓                          │
│  混合合并器 → 去重 + 置信度优选  │
│       ↓                          │
│  输出: KnowledgePoint[]          │
│  每个含: name, description,      │
│         tags[{value, category}], │
│         confidence, method       │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  5. 题目生成 (questions/)        │
│                                  │
│  对每个知识点:                   │
│    根据 tag.category 选 Prompt   │
│    调用 LLM 生成题目             │
│    并发执行 (asyncio.to_thread)  │
│       ↓                          │
│  失败时生成占位题干              │
│       ↓                          │
│  输出: QuestionStem[]            │
│  含: stem_text, options[],       │
│      correct_answer, explanation │
└─────────────────────────────────┘
```

### 关键端点

| 端点 | 触发阶段 |
|------|----------|
| `POST /extract` | 仅文档解析 |
| `POST /structure` | 解析 + 章节检测 |
| `POST /knowledge` | 解析 + 章节 + 知识点提取 |
| `POST /questions/generate/from-file` | 完整管线：解析 → 章节 → 知识点 → 题目 |
| `POST /questions/generate` | 仅从知识点列表生成题目 |

管线是**可拆分的**——前端可以选择只调用部分端点，也可以调用完整管线端点一步到位。

## 路径 B：WebSocket 对话 Agent

适用于交互式场景：用户通过聊天对话，Agent 自动判断意图并调度工具。

```
用户发送消息
     │
     ▼
┌──────────────────────────────────────────────┐
│  WebSocket 连接 (/ws/chat)                    │
│  如果选择了知识库: 消息前缀加 [kb:<id>]        │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│  LangGraph StateGraph                        │
│                                              │
│  START → dispatch → ┬→ tools → chat → ┬→ END │
│                     └→ chat ──────────┘      │
│                                              │
│  dispatch_node: 意图分类                      │
│    ├─ extract  → 强制调用 extract_knowledge   │
│    ├─ generate → 强制调用 generate_questions  │
│    │              或 fetch_knowledge_from_kb  │
│    └─ chat     → 直接进 chat_node            │
│                                              │
│  chat_node: LLM 对话（带工具绑定）            │
│    └─ 如果 LLM 返回 tool_calls → 回到 tools  │
│                                              │
│  tools node: 执行工具调用                     │
│    └─ 工具结果返回后 → 进入 chat_node 总结    │
└──────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│  流式响应 (JSON 事件流)                       │
│  {type: "start"}    → 开始生成               │
│  {type: "token"}    → 文本 token 流          │
│  {type: "data"}     → 工具结果（知识点/题目） │
│  {type: "end"}      → 生成结束               │
│  {type: "history"}  → 历史消息（重连恢复）    │
│  {type: "error"}    → 错误信息               │
└──────────────────────────────────────────────┘
```

## 两条路径的差异

| 维度 | REST 管线 | WebSocket Agent |
|------|-----------|-----------------|
| 交互方式 | 一次性请求/响应 | 多轮对话 |
| 输入来源 | 文件上传 | 文本输入或知识库 |
| 章节检测 | 完整管线 | 不涉及（Agent 直接处理文本） |
| 知识点提取 | 先窗口分割再提取 | 整段文本一次提取 |
| 题目生成 | 批量并发 | 通过工具调用，单次批量 |
| 状态管理 | 无状态 | LangGraph checkpoint 持久化 |
| 流式输出 | 不支持 | 支持 token 级流式 |
| 知识库集成 | 独立 API | Agent 工具自动调度 |

## 数据模型流转

```
文件上传路径的数据模型链:

UploadFile
  → paragraphs: [{text, font_size, is_bold, style_name, page_number}]
  → ChapterHeading: {line_index, level, title, confidence, method}
  → ChapterNode: {id, title, level, line_start, line_end, children[]}
  → ChapterWindow: {chapter_id, chapter_title, text, line_start, line_end}
  → KnowledgePoint: {id, name, description, tags[], confidence, method, source_line_*}
  → QuestionStem: {id, stem_text, options[], correct_answer, explanation, ...}

对话路径的数据模型链:

UserMessage
  → IntentType: "extract" | "generate" | "chat"
  → ToolCall (forced): {name, args, id}
  → ToolMessage: JSON string (知识点列表 or 题目列表)
  → AIMessage: LLM 自然语言回复 + 可选 tool_calls
```
