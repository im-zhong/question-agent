# 05 - LangGraph 对话 Agent

对话 Agent 是本系统最复杂的组件。它不是一个简单的 "聊天机器人"，而是一个**带工具调度的状态机**，能根据用户意图自动选择执行知识提取或出题任务。

## 为什么选择 LangGraph

| 特性 | 纯 LLM 对话 | LangGraph Agent |
|------|-------------|-----------------|
| 工具调用 | 需 LLM 自主决定 | 可编程强制调度 |
| 状态持久化 | 需自行实现 | 内置 checkpoint |
| 流式输出 | 需自行实现 | 内置 streaming |
| 执行流程控制 | 线性 | 图结构，支持条件分支 |
| 对话恢复 | 需自行实现 | checkpointer 自动恢复 |

## StateGraph 架构

```
              ┌─────────────────────────────────────────┐
              │                                         │
              │   START                                  │
              │     │                                    │
              │     ▼                                    │
              │  ┌──────────┐                           │
              │  │ dispatch │ 意图分类 + 强制工具调用      │
              │  └────┬─────┘                           │
              │       │                                 │
              │  ┌────┴────────────┐                    │
              │  │ conditional     │                    │
              │  │ _route_after_   │                    │
              │  │ dispatch        │                    │
              │  └──┬──────────┬──┘                    │
              │     │          │                        │
              │ has_tool_call  no_tool_call             │
              │     │          │                        │
              │     ▼          ▼                        │
              │  ┌────────┐  ┌──────────┐              │
              │  │ tools  │  │  chat    │              │
              │  │(ToolNode)│  │  (LLM)  │              │
              │  └───┬────┘  └────┬─────┘              │
              │      │            │                     │
              │      │      ┌─────┴──────────┐          │
              │      │      │ conditional    │          │
              │      │      │ _should_       │          │
              │      │      │ continue       │          │
              │      │      └──┬──────────┬──┘          │
              │      │         │          │             │
              │      │  has_tool_call  no_tool_call     │
              │      │         │          │             │
              │      │         ▼          ▼             │
              │      │      ┌────────┐   END            │
              │      │      │ tools  │                   │
              │      │      └───┬────┘                   │
              │      │          │                        │
              │      ▼          ▼                        │
              │  ┌──────────┐                           │
              │  │  chat    │ ◄─────── tools 结果       │
              │  │  (LLM)   │         汇入 chat_node     │
              │  └──────────┘                           │
              │       │                                 │
              │       ▼                                 │
              │      END                                │
              └─────────────────────────────────────────┘
```

## 意图分类 (dispatch_node)

这是 Agent 的入口节点，决定后续走向。

### 分类规则

```python
def classify_intent(message):
    # 规则 1: 长文本（>= 200 字符）→ 提取知识点
    if len(message.strip()) >= 200:
        return "extract"

    # 规则 2: 包含出题关键词 → 生成题目
    for keyword in ["出题", "生成题", "练习题", "考试题", "选择题", ...]:
        if keyword in message:
            return "generate"

    # 规则 3: 默认 → 普通对话
    return "chat"
```

### 强制工具调用机制

这是本系统最关键的设计之一：**不依赖 LLM 决定是否调用工具，而是由 dispatch_node 程序化地强制注入工具调用**。

```python
if intent == "extract":
    # 创建一个合成的 AIMessage，包含强制工具调用
    tool_call = {
        "name": "extract_knowledge_points",
        "args": {"text": raw_content},
        "id": "forced_extract",
        "type": "tool_call",
    }
    synthetic_ai = AIMessage(content="", tool_calls=[tool_call])

elif intent == "generate":
    if kb_id:
        tool_call = {
            "name": "fetch_knowledge_points_from_kb",
            "args": {"kb_id": kb_id},
            ...
        }
    else:
        # 从对话历史中搜索之前提取的知识点
        kp_json = _extract_kp_from_history(messages)
        if kp_json is None:
            # 没有知识点，提示用户提供
            return SystemMessage("请先提供教材内容")
        tool_call = {
            "name": "generate_questions",
            "args": {"knowledge_points_json": kp_json},
            ...
        }
```

**为什么不直接让 LLM 决定？**

1. **可靠性**——LLM 可能不调用工具，或调用错误的工具
2. **成本**——让 LLM 决策需要额外一轮 API 调用
3. **确定性**——关键词匹配的意图分类是确定性的，容易测试和调试

### 知识库上下文

当用户在对话中选择了知识库时，前端会自动在消息前添加 `[kb:<id>]` 前缀：

```
原始消息: "[kb:a1b2c3] 帮我出5道选择题"
解析后: kb_id = "a1b2c3", content = "帮我出5道选择题"
```

dispatch_node 根据是否有 kb_id 决定走哪条工具路径：

- **有 kb_id + generate 意图** → `fetch_knowledge_points_from_kb` (从数据库获取知识点)
- **无 kb_id + generate 意图** → `generate_questions` (从对话历史获取知识点)
- **extract 意图** → `extract_knowledge_points` (从用户文本实时提取)

## 三个 Agent 工具

### 1. extract_knowledge_points

```python
@tool
def extract_knowledge_points(text: str) -> str:
    """从教材文本中提取知识点。"""

    # 将文本分割为段落
    paragraphs = [{"text": line.strip()} for line in text.split("\n")]

    # 构造 ChapterWindow
    window = ChapterWindow(chapter_id="doc_full", text=text, ...)

    # 调用混合提取管线
    result = extract_knowledge_points_hybrid([window], paragraphs)

    # 返回 JSON
    return json.dumps(output, ensure_ascii=False)
```

### 2. fetch_knowledge_points_from_kb

```python
@tool
async def fetch_knowledge_points_from_kb(kb_id: str) -> str:
    """从知识库中获取所有知识点。"""

    kb = await get_kb(kb_id)
    if kb is None:
        return json.dumps({"error": "知识库不存在"})

    kps = await list_kbs_knowledge_points(kb_id)
    if not kps:
        return json.dumps({"error": "知识库中没有知识点"})

    return json.dumps(result, ensure_ascii=False)
```

### 3. generate_questions

```python
@tool
def generate_questions(knowledge_points_json: str, question_type: str | None = None) -> str:
    """根据知识点列表生成题目。"""

    # 解析知识点 JSON
    kp_list = json.loads(knowledge_points_json)

    # 从已有事件循环中运行异步生成器
    # 使用 ThreadPoolExecutor 避免嵌套事件循环问题
    with concurrent.futures.ThreadPoolExecutor() as pool:
        questions, stats = pool.submit(
            asyncio.run, generate_questions(inputs, question_type=question_type)
        ).result()

    return json.dumps(output, ensure_ascii=False)
```

**注意**：`generate_questions` 工具是同步函数，但内部调用了异步的 `generate_questions` 管线。使用 `ThreadPoolExecutor + asyncio.run` 解决了 LangGraph 同步工具中运行异步代码的问题。

## 条件路由

### _route_after_dispatch

```
dispatch_node 输出后:
  最后一条消息是 AIMessage 且有 tool_calls → "tools"
  否则 → "chat"
```

### _should_continue

```
chat_node 输出后:
  最后一条消息是 AIMessage 且有 tool_calls → "tools" (继续)
  否则 → END (结束)
```

这意味着 LLM 可以自主发起多轮工具调用——如果它在回复中包含了新的 tool_calls，Agent 会继续执行。

## 对话状态持久化

使用 LangGraph 的 `AsyncSqliteSaver` 将对话状态保存到 SQLite：

```python
checkpointer = AsyncSqliteSaver(conn=aiosqlite_connection)
graph = graph.compile(checkpointer=checkpointer)
```

- **存储位置**: `data/chat.db`
- **存储内容**: 完整消息历史（Human/AI/Tool/System 消息）
- **恢复机制**: 传入 `conversation_id` 作为 `thread_id`，Graph 自动从 checkpoint 恢复
- **自动管理**: 每次图执行后自动保存

## 流式响应协议

WebSocket 流式输出遵循以下 JSON 事件协议：

```
事件类型          方向           内容
─────────────────────────────────────────────────
start           Server → Client  空事件，标记开始
token           Server → Client  {"content": "文本片段"}
data            Server → Client  {"tool": "工具名", "content": "JSON"}
end             Server → Client  空事件，标记结束
history         Server → Client  {"messages": [...]}
error           Server → Client  {"content": "错误信息"}
```

### 前端处理逻辑

```
收到 start   → 创建空的 assistant 消息气泡
收到 token   → 追加文本到当前消息（流式打字效果）
收到 data    → 解析 JSON，渲染知识点卡片或题目卡片
收到 end     → 完成当前消息
收到 history → 重连时恢复对话历史
收到 error   → 显示错误提示
```

### 消息类型映射

```
LangGraph 消息类型 → WebSocket 事件 → 前端渲染
────────────────────────────────────────────────
AIMessageChunk      → token          → Markdown 流式渲染
ToolMessage         → data           → 结构化卡片（知识点/题目）
AIMessage (final)   → token + end    → 完整 Markdown
SystemMessage       → token          → 系统提示文本
```

## 题型检测

除了意图分类，`intent.py` 还包含题型检测：

```python
def detect_question_type(message):
    # 论述题关键词
    for keyword in ["论述", "论述题", "分析题", "作文题"]:
        if keyword in message:
            return "essay"

    # 简答题关键词
    for keyword in ["简答", "简答题", "填空", "简述"]:
        if keyword in message:
            return "short_answer"

    # 默认：选择题
    return None
```

检测到的 `question_type` 会传入 `generate_questions` 工具的参数，影响 Prompt 选择。
