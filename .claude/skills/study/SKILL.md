---
name: study
description: Research topics, teach interactively, build demos, and save structured learning notes to the project knowledge base
argument-hint: "<topic>"
triggers:
  - "study"
  - "/study"
  - "学习"
  - "teach me"
  - "explain"
  - "walk me through"
level: 4
---

<Purpose>
  交互式学习工具。研究主题 → 教学 → 构建可运行 demo → 生成结构化笔记。
  知识沉淀到项目仓库 `notes/` 目录，随项目版本管理。
</Purpose>

<Use_When>
  - 想学习一个技术主题（"teach me async/await"）
  - 想生成参考笔记（"write notes on X"）
  - 想在项目中积累工程知识
  - 用户说 "study"、"teach me"、"explain"、"学习"
</Use_When>

<Do_Not_Use_When>
  - 纯查文档 — 用 WebSearch 即可
  - 需要项目专属的 bug-fix 经验沉淀 — 用 learner 技能（~/.claude/skills/learner/）
</Do_Not_Use_When>

<Execution_Policy>
  - 解析请求 → 准备存储 → 委托 study-agent → 更新索引
  - 技能只做路由和持久化，教学逻辑在 agent
</Execution_Policy>

<Steps>

### Step 1: Parse Request

从用户输入中提取：
- **topic**: 学习主题（如 "Python async/await"）
- **mode**: 对话式 or 自主输出

| 关键词 | Mode |
|--------|------|
| "teach me", "explain", "how does", "walk me through" | conversational |
| "write notes on", "reference on", "summarize", "cheatsheet" | autonomous |

默认 conversational。

### Step 2: Check Existing Notes

Read `notes/INDEX.md`（如果存在）。
如果 topic 已有笔记，询问用户：更新已有笔记还是创建新条目。

### Step 3: Prepare Storage

```bash
mkdir -p notes/{category}/{topic-slug}/demo/
```

- **category**: 从 topic 推断（python / javascript / databases / devops / ...），不确定时用 "general"
- **topic-slug**: 小写、hyphenated（如 "async-await"）

### Step 4: Select Format

| 内容类型 | 格式 |
|----------|------|
| 代码为主、可运行示例 | `.ipynb` |
| 概念、架构、理论 | `.md` + mermaid |
| 参考文档、API、配置 | `.md` |

不确定时默认 `.md`。

### Step 5: Delegate to study-agent

```
Task(
  description="Study: <topic>",
  subagent_type="oh-my-claudecode:study-agent",
  model="opus",
  prompt="
    Topic: <topic>
    Mode: <conversational | autonomous>
    Notes path: notes/<category>/<topic-slug>/index.<md|ipynb>
    Demo dir: notes/<category>/<topic-slug>/demo/
    Existing notes: <path or 'none'>
  "
)
```

### Step 6: Finalize

Agent 完成后：
1. 验证笔记文件已写入
2. 更新 `notes/INDEX.md`：追加新条目
3. 报告文件路径给用户

</Steps>

<Tool_Usage>
  - Bash: mkdir -p 创建目录
  - Read: 读取 INDEX.md 和已有笔记
  - Task(subagent_type="oh-my-claudecode:study-agent", model="opus"): 委托教学
  - Write: 更新 INDEX.md
</Tool_Usage>

<Escalation>
  - topic 模糊 → 用 AskUserQuestion 澄清
  - demo 运行失败 → agent 内部重试一次，仍失败则在笔记中添加 Known Issue
  - INDEX.md 不存在 → 新建
</Escalation>
