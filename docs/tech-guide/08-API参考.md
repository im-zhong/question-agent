# 08 - API 参考

## 基础信息

- 后端地址: `http://localhost:8000`
- 开发代理: 前端 `/api` → 后端 `/`（去除 `/api` 前缀）
- WebSocket: `ws://localhost:8000/ws/chat`

## 健康检查

### `GET /health`

```
Response: {"status": "ok"}
```

---

## WebSocket 对话

### `WS /ws/chat`

**连接参数** (query string):

| 参数 | 类型 | 说明 |
|------|------|------|
| conversation_id | string | 可选，恢复已有对话 |

**客户端发送消息格式**:

```json
{
  "conversation_id": "conv_123",
  "content": "帮我出5道关于牛顿定律的选择题"
}
```

**服务端事件格式**:

```json
// 开始
{"type": "start"}

// 文本 token（流式）
{"type": "token", "content": "好的"}

// 工具结果
{"type": "data", "tool": "extract_knowledge_points", "content": "[...]"}
{"type": "data", "tool": "generate_questions", "content": "{...}"}
{"type": "data", "tool": "fetch_knowledge_points_from_kb", "content": "[...]"}

// 结束
{"type": "end"}

// 历史消息（重连时）
{"type": "history", "messages": [...]}

// 错误
{"type": "error", "content": "错误描述"}
```

**知识库前缀**: 如果用户选择了知识库，content 应添加前缀 `[kb:<id>]`

---

## 文档解析

### `POST /extract`

上传文件并提取文本内容。

**请求**: `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | PDF/DOCX/TXT 文件 |
| mode | string | 否 | `"text"` (默认) 或 `"structured"` |

**响应** (`mode=text`):

```json
{
  "text": "完整文本内容..."
}
```

**响应** (`mode=structured`):

```json
{
  "paragraphs": [
    {
      "text": "段落文本",
      "font_size": 14,
      "is_bold": false,
      "style_name": "Normal",
      "page_number": 1
    }
  ]
}
```

---

## 章节结构

### `POST /structure`

从上传文件检测章节结构。

**请求**: `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | 文档文件 |

**响应**:

```json
{
  "headings": [
    {
      "line_index": 5,
      "level": 1,
      "title": "第一章 绪论",
      "confidence": 0.95,
      "method": "style"
    }
  ],
  "detection_method": "hybrid",
  "rule_count": 3,
  "llm_count": 2
}
```

---

## 知识点提取

### `POST /knowledge`

完整管线：文件上传 → 解析 → 章节检测 → 知识点提取。

**请求**: `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | 文档文件 |

**响应**:

```json
{
  "paragraphs": [...],
  "chapters": {
    "headings": [...],
    "detection_method": "hybrid"
  },
  "knowledge_points": [
    {
      "id": 0,
      "name": "加速度",
      "description": "速度变化量与发生这一变化所用时间的比值",
      "tags": [{"value": "加速度", "category": "concept"}],
      "confidence": 0.85,
      "method": "llm",
      "source_line_start": 10,
      "source_line_end": 12
    }
  ],
  "detection_method": "hybrid",
  "rule_count": 5,
  "llm_count": 8
}
```

---

## 题目生成

### `POST /questions/generate`

从知识点列表生成题目。

**请求**: `application/json`

```json
{
  "knowledge_points": [
    {
      "name": "加速度",
      "description": "速度变化量与时间的比值",
      "tags": [{"value": "加速度", "category": "concept"}]
    }
  ],
  "difficulty": "intermediate",
  "question_type": null
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| knowledge_points | array | 是 | 知识点列表 |
| difficulty | string | 否 | `"basic"` / `"intermediate"` / `"advanced"` |
| question_type | string | 否 | `"short_answer"` / `"essay"` / null (选择题) |

**响应**:

```json
{
  "questions": [
    {
      "id": 1,
      "stem_text": "加速度的定义是指以下哪个？",
      "options": [
        {"label": "A", "text": "速度变化量与时间的比值"},
        {"label": "B", "text": "位移与时间的比值"},
        {"label": "C", "text": "速度与时间的乘积"},
        {"label": "D", "text": "力与质量的比值"}
      ],
      "correct_answer": "A",
      "explanation": "加速度定义为Δv/Δt",
      "knowledge_point_name": "加速度",
      "question_type": "concept",
      "difficulty": "intermediate",
      "status": "success"
    }
  ],
  "stats": {
    "total": 1,
    "successful": 1,
    "failed": 0
  }
}
```

### `POST /questions/generate/from-file`

完整管线：文件 → 知识点 → 题目。

**请求**: `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | 文档文件 |
| difficulty | string | 否 | 默认 `"intermediate"` |
| question_type | string | 否 | 默认 null (选择题) |

**响应**: 同 `POST /questions/generate`，但额外包含 `chapters` 和 `knowledge_points` 信息。

### `POST /questions/export`

导出题目为 Markdown 或 JSON 格式。

**请求**: `application/json`

```json
{
  "questions": [...],
  "format": "markdown"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| questions | array | 是 | QuestionStem 列表 |
| format | string | 否 | `"markdown"` (默认) 或 `"json"` |

---

## 知识库管理

### `POST /v1/knowledge-bases`

创建知识库。

```json
{
  "name": "高中物理",
  "description": "高中物理教材知识点",
  "subject": "物理",
  "grade_level": "高中"
}
```

**响应**:

```json
{
  "id": "a1b2c3d4e5f6...",
  "name": "高中物理",
  "description": "高中物理教材知识点",
  "subject": "物理",
  "grade_level": "高中",
  "document_count": 0,
  "created_at": "2025-01-15T10:30:00+00:00",
  "updated_at": "2025-01-15T10:30:00+00:00"
}
```

### `GET /v1/knowledge-bases`

列表所有知识库。

**响应**: `KnowledgeBase[]`，按 `created_at` 倒序。

### `DELETE /v1/knowledge-bases/{id}`

删除知识库及其所有文档和知识点。

**响应**: `204 No Content`

### `POST /v1/knowledge-bases/{id}/documents`

上传文档到知识库（自动触发知识点提取）。

**请求**: `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | PDF/DOCX/TXT 文件 |

**响应**:

```json
{
  "document": {
    "id": "d1e2f3...",
    "kb_id": "a1b2c3...",
    "filename": "第一章.pdf",
    "format": "pdf",
    "char_count": 15000,
    "status": "completed",
    "created_at": "..."
  },
  "knowledge_point_count": 12,
  "knowledge_points": [...]
}
```

### `GET /v1/knowledge-bases/{id}/documents`

列表知识库中的文档。

**响应**: `Document[]`

### `GET /v1/knowledge-bases/{id}/knowledge-points`

列表知识库中的所有知识点。

**响应**: `KnowledgePoint[]`

---

## 错误响应

所有 REST 端点在出错时返回统一格式：

```json
{
  "detail": "错误描述信息"
}
```

常见 HTTP 状态码：

| 状态码 | 含义 |
|--------|------|
| 422 | 请求参数校验失败 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 配置

后端通过 `.env` 文件配置：

```env
GLM_API_KEY=your_zhipu_api_key
GLM_MODEL=glm-5-flash
CHAT_DB_PATH=data/chat.db
KB_DB_PATH=data/kb.db
```

前端通过环境变量配置：

```env
VITE_API_URL=http://localhost:8000  # 生产环境 API 地址
```
