---
name: summarize
description: Phase summary report — bridges iterations by synthesizing code, docs, and web research into a structured handoff for the next pre-dev cycle
argument-hint: ""
triggers:
  - "summarize"
  - "summary"
  - "阶段总结"
  - "迭代总结"
level: 4
---

<Purpose>
  承上启下。将本轮 dev 产出的代码、文档和 web search 知识合成为一份结构化总结报告，
  喂给下一轮 pre-dev，让 pre-dev 知道"做到了哪里、什么是新的、下一步优先做什么"。
</Purpose>

<Use_When>
  - 一个 Phase 或 dev 周期完成后，需要总结现状
  - 下一轮 pre-dev 开始前，需要上下文
  - 用户说 "summarize"、"总结一下"、"写个阶段报告"
</Use_When>

<Do_Not_Use_When>
  - dev 还没开始 — 无内容可总结
  - 项目刚 pre-dev 完还没写代码 — 直接用 pre-dev 的 summary 即可
</Do_Not_Use_When>

<Execution_Policy>
  - 收集上下文 (read + git + web search)，不做推理
  - 委托 summarize-agent (opus, read-only) 合成报告
  - 报告写入后更新 state.md
  - 上下文不完整时报错，不生成空报告
</Execution_Policy>

<Steps>

### Step 1: Load State

读取 `docs/superpowers/state.md`。
- 不存在 → 从 git log + 文档目录自动推断重建（走 Step 1a）
- 存在 → 解析 frontmatter 和文档快照表，获取 spec/roadmap/toolchain 路径

**Step 1a: 重建 state.md (state 缺失时)**
1. `git log --oneline -20` 获取迭代线索
2. Glob `docs/superpowers/specs/*.md`、`plans/*.md`、`summaries/*.md`、`.harness/*-toolchain.md`
3. 推断迭代次数和阶段
4. 创建最小 state.md（后续 status 技能可完善）

### Step 2: Collect Context (并行)

同时执行以下读取：

| 操作 | 工具 | 说明 |
|------|------|------|
| 读取 spec | Read | 从 state.md 文档快照获取路径 |
| 读取 roadmap | Read | 同上 |
| 读取 toolchain | Read | 同上 |
| 读取上一轮 summary | Read | 如果 frontmatter.previous 存在 |
| Git log | Bash: `git log --oneline -15` | 最近 commit 历史 |
| Git diff stat | Bash: `git diff --stat HEAD~10..HEAD 2>/dev/null \|\| git diff --stat $(git rev-list --max-parents=0 HEAD)..HEAD` | 代码变更概览 |
| 测试结果 | Bash: `uv run pytest --tb=short 2>&1 \| tail -25` | 测试通过率和失败详情 |
| WebSearch × 3 | WebSearch | 同类方案、新技术趋势、当前技术栈最佳实践 |

WebSearch 查询方向（基于 spec 中的功能领域 + toolchain 中的技术栈）：
- "<功能领域> 实现方案 最佳实践"
- "<技术栈> 最新版本 新特性"
- "<功能领域> 常见坑 经验"

WebSearch 失败不阻塞，跳过 E section。

### Step 3: Delegate to summarize-agent

```
Task(
  description="Generate phase summary report",
  subagent_type="oh-my-claudecode:summarize-agent",
  model="opus",
  prompt="
    ## 状态
    Iteration: <frontmatter.iteration>
    Phase: <frontmatter.current_phase>
    Date: <today>

    ## 上一轮 Summary
    <previous summary content, or 'N/A (first iteration)'>

    ## Spec
    <spec content>

    ## Roadmap
    <roadmap content>

    ## Toolchain
    <toolchain content>

    ## Git Log (recent 15)
    <git log output>

    ## Code Changes (diff stat)
    <diff stat output>

    ## Test Results
    <pytest output>

    ## Web Search Results
    <web search results>

    ## 指令
    生成一份承上启下的 10-section 迭代总结报告。格式要求见下方 Output Format。
    文本控制在 200 行以内（不含 mermaid）。
    核心原则：
    - 承上：从 diff/log 中提炼实际做了什么，对比 spec 标注偏差
    - 启下：基于遗留 + 知识 + 教训，给出具体优先建议（"优先 X，因为 Y"）
    - 精炼：每句话有信息量，不写废话
    - 客观：区分事实和判断，判断标注推理依据

    ## Output Format
    ```markdown
    ---
    iteration: <N>
    phase: \"<phase>\"
    date: <today>
    status: complete
    previous: <path to previous summary or null>
    ---

    # 总结报告 — <today>

    ## A. 本轮完成
    ...（功能级别，3-8 条）

    ## B. 代码变更
    ...（diff stat 表格 + 关键变化意图说明）

    ## C. 文档现状
    ...（spec/roadmap/toolchain 状态表格）

    ## D. 遗留问题
    ...（未完成决定、已知 bug、技术债、延迟决策）

    ## E. 外部知识
    ...（web search 发现的洞察，3-5 条）

    ## F. 下一轮建议
    ...（具体优先建议，带理由）

    ## G. 量化统计
    ...（commits/文件/行数/测试 表格）

    ## H. 架构快照
    ...（mermaid 图，标注本轮改动模块）

    ## J. 关键决策
    ...（ADR 风格 — 决定 + 为什么 + 后果）

    ## K. 经验教训
    ...（顺利/困难/意外的发现）
    ```
  "
)
```

Agent 返回完整报告后，写入 `docs/superpowers/summaries/<date>-summary.md`。

### Step 4: Present Summary

展示报告摘要（5-8 行精炼版）给用户，带完整文件路径。

```
## Summarize 完成

报告: docs/superpowers/summaries/<date>-summary.md
本轮: 完成 <N> 个功能 / <M> commits / <X> 行代码变更
下一轮建议: <F section 的 top 1-2 条>

→ 运行 /pre-dev "<描述>" 开始下一轮迭代
```

### Step 5: Update State

更新 `docs/superpowers/state.md`：
1. 更新 frontmatter: `current_phase: summarize`, `updated: <today>`
2. 追加迭代文件 (`docs/superpowers/iterations/NN-date.md`) 流程行：`| summarize | <date> | [summary](summaries/<date>-summary.md) | ✅ |`
3. 更新文档快照表：新增 summary 行
4. 如果当前迭代无遗留阶段，标记迭代完成

</Steps>

<Tool_Usage>
  - Read: 读取 spec/roadmap/toolchain/state/previous-summary
  - Bash: git log, git diff --stat, uv run pytest
  - WebSearch: 同类方案 × 3
  - Task(subagent_type="oh-my-claudecode:summarize-agent", model="opus"): 委托报告合成
  - Write: 写入 summaries/<date>-summary.md, 更新 state.md, 更新 iterations/NN-date.md
</Tool_Usage>

<Escalation>
  - spec 或 roadmap 缺失 → 提示用户先运行 /pre-dev
  - git 仓库无任何 commit → 跳过 diff stat，标注 "无历史记录"
  - WebSearch 全部失败 → E section 标注 "本次无外部知识注入"，不阻塞
  - summarize-agent 生成超 300 行 → 要求精简到 200 行以内再写入
</Escalation>

<Final_Checklist>
  - [ ] state.md 加载成功（或重建完成）
  - [ ] 全部上下文并行收集完成
  - [ ] summarize-agent 委托完成并返回报告
  - [ ] 报告写入 summaries/<date>-summary.md
  - [ ] 用户看到摘要
  - [ ] state.md 和迭代文件已更新
</Final_Checklist>
