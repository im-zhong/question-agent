# Summarize Inline Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge summarize-agent's synthesis logic into the summarize skill, making it a pure skill with no subagent delegation.

**Architecture:** Rewrite `.claude/skills/summarize/SKILL.md` Step 3 from "Delegate to summarize-agent" to "Synthesize Report", inlining all agent content (Synthesis_Protocol, Section_Guidance, Success_Criteria, Constraints, Failure_Modes_To_Avoid). Then delete `.claude/agents/summarize-agent.md`.

**Tech Stack:** Markdown skill/agent definitions for Claude Code harness

---

### Task 1: Rewrite summarize SKILL.md

**Files:**
- Modify: `.claude/skills/summarize/SKILL.md` (full rewrite)

This is a single task because the changes are deeply interconnected — Execution_Policy references Step 3, Tool_Usage references the removed Task() call, Final_Checklist references the removed delegation. Splitting into partial edits would create inconsistent intermediate states.

- [ ] **Step 1: Write the new SKILL.md**

Replace the entire content of `.claude/skills/summarize/SKILL.md` with:

```markdown
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
  - 收集上下文 (read + git + web search)
  - 直接合成 10-section 结构化报告（不委托子代理）
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

### Step 3: Synthesize Report

将本轮 dev 产出的代码、文档和 web search 知识合成为一份结构化总结报告。没有刻意总结，每个 pre-dev 周期就会盲目开始，重新发现分散在 repo 中的上下文。

**Synthesis Protocol:**

1. **Absorb inputs** — 读取所有已收集的上下文：spec、roadmap、toolchain、git log、diff stat、test results、web search findings、previous summary
2. **Cross-reference** — 对比 git diff/log 与 spec/roadmap，标注偏差。实现是否匹配计划？
3. **Extract decisions** — 扫描 git log 和 diff 提炼架构决策：新模块、重构接口、依赖变更
4. **Categorize findings** — 事实（做了什么）→ A/B/C/G/H，判断（意味着什么）→ D/E/F/J/K
5. **Draft report** — 写所有 section。空 section 说明原因（如 "无外部知识 — web search 失败"），不删除 section
6. **Trim to 200 lines** — 削弱冗余示例、冗长描述、显而易见的声明。保留具体细节
7. **Self-check** — 扫描捏造：每项声明必须可溯源到输入。验证 frontmatter 字段与 state 输入匹配

**Output Format:**

```markdown
---
iteration: <N>
phase: "<phase name>"
date: <YYYY-MM-DD>
status: complete
previous: <path to previous summary or null>
---

# 总结报告 — <YYYY-MM-DD>

## A. 本轮完成
...

## B. 代码变更
...

## C. 文档现状
...

## D. 遗留问题
...

## E. 外部知识
...

## F. 下一轮建议
...

## G. 量化统计
...

## H. 架构快照
```mermaid
...
```

## J. 关键决策
...

## K. 经验教训
...
```

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

<Synthesis_Rules>

<Success_Criteria>
  - 全部 10 section 存在且有实质内容（无 TBD 占位）
  - "承上" sections (A/B/C/G/H) 基于实际代码 diff、git log、test output — 非推测
  - "启下" sections (D/E/F/J/K) 可操作 — 具体建议带理由，非泛泛之谈
  - 报告 ≤ 200 行文本（mermaid 除外）
  - 事实与判断清晰区分
  - 每个判断/建议有可见的推理链路回到输入证据
</Success_Criteria>

<Constraints>
  - 不捏造 — 输入缺失时明确标注（如 "无测试结果 — 跳过"），不猜测
  - 架构图必须标注本轮改动 — 使用 mermaid `style` 指令或颜色注释
  - 外部知识（E section）必须引用来源 — 域名或论文标题，非原始 URL
</Constraints>

<Section_Guidance>

### A. 本轮完成

- 功能级别描述，非文件级别。"实现了题目录入 API" 而非 "写了 questions.py"
- 3-8 条。合并琐碎项
- 对比 spec/roadmap："（按 plan 完成）" 或 "（偏差：多做了 CSV 导入，plan 未包含）"

### B. 代码变更

- diff stat 表格：文件路径 | 新增行数 | 删除行数 | 简要说明
- 仅列 Top 5-8 变更文件 — 不列每个文件
- 2-3 句话说明关键架构变化意图

### C. 文档现状

- 表格：文档类型 | 路径 | 状态（confirmed/draft/needs-update）
- 标注过期文档："spec 未反映 CSV 导入，建议更新"

### D. 遗留问题

- 带上下文的 bullet list：什么是未决定的、为什么延迟、什么阻碍解决
- 区分："决定延迟到 Phase 2" vs "真的不知道怎么做"

### E. 外部知识

- 仅包含 web search 的可操作洞察
- 每条：洞察 → 与本项目的关系
- 最多 3-5 条。web search 失败时标注并跳过

### F. 下一轮建议

- 具体，按优先级排序
- 每条："优先做 X，因为 Y"
- 基于 D section（遗留）+ E section（新知）+ K section（教训）
- 不是 roadmap — pre-dev 会建那个。这是方向性输入

### G. 量化统计

- 表格：commits | files changed | lines added/deleted | test pass rate | new tests
- 从 git diff --stat 和 pytest 输出提取

### H. 架构快照

- Mermaid 图展示当前系统结构
- 使用 style/颜色标注本轮改动（绿色=新增，黄色=修改）
- 保持可读 — 最多 10 节点
- 简短说明图表含义

### J. 关键决策

- ADR-lite 格式：决定 / 原因 / 后果
- 每迭代 1-3 个决策（多数迭代只有少数真正的决策）
- 只包含实际做出并提交的决策 — 不是 "我们考虑了 X"

### K. 经验教训

- 三类：✅ 比预期顺利 / ⚠️ 比预期困难 / 💡 意外发现
- 具体："CSV 解析器用标准库 csv 模块即可，不需要 pandas" 而非 "工具选择成功"
- 直接为 F section（下一轮建议）提供输入

</Section_Guidance>

<Failure_Modes_To_Avoid>

- **重复 spec：** 不列计划了什么。列对照计划做了什么
- **空泛建议：** "继续完善功能" 无用。"优先实现自动组卷算法，因为手动选题已是瓶颈" 有用
- **捏造决策：** diff 中找不到架构决策就不发明。跳过 J 或标注 "本轮无新的架构决策"
- **过详架构图：** ≤ 10 节点。这是快照，不是完整系统蓝图
- **忽略测试失败：** 如果测试失败，D section 必须包含失败。F section 应应对
- **冗长教训：** 每类最多 2-3 条。"比预期困难：题目校验边界情况多" 胜过一段话
- **浅薄外部知识：** "用 React 做前端" 不是洞察。"React 19 的 Server Components 可以减少题库系统的首屏加载时间" 是洞察

</Failure_Modes_To_Avoid>

</Synthesis_Rules>

<Tool_Usage>
  - Read: 读取 spec/roadmap/toolchain/state/previous-summary
  - Bash: git log, git diff --stat, uv run pytest
  - WebSearch: 同类方案 × 3
  - Write: 写入 summaries/<date>-summary.md, 更新 state.md, 更新 iterations/NN-date.md
</Tool_Usage>

<Escalation>
  - spec 或 roadmap 缺失 → 提示用户先运行 /pre-dev
  - git 仓库无任何 commit → 跳过 diff stat，标注 "无历史记录"
  - WebSearch 全部失败 → E section 标注 "本次无外部知识注入"，不阻塞
  - 报告超 200 行 → 自检精简到 200 行以内再写入
</Escalation>

<Final_Checklist>
  - [ ] state.md 加载成功（或重建完成）
  - [ ] 全部上下文并行收集完成
  - [ ] 报告合成完成
  - [ ] 全部 10 section 存在
  - [ ] 事实可溯源到输入
  - [ ] 判断有推理依据
  - [ ] 架构图标注改动
  - [ ] 建议具体且按优先级排序
  - [ ] ≤ 200 行文本
  - [ ] 无捏造、无占位 section
  - [ ] 报告写入 summaries/<date>-summary.md
  - [ ] 用户看到摘要
  - [ ] state.md 和迭代文件已更新
</Final_Checklist>
```

- [ ] **Step 2: Verify the new SKILL.md is syntactically valid**

Run: `cat .claude/skills/summarize/SKILL.md | head -5`
Expected: Shows the frontmatter with `name: summarize`

Run: `grep -c "summarize-agent" .claude/skills/summarize/SKILL.md`
Expected: 0 (no references to the removed agent)

Run: `grep -c "Synthesis_Protocol" .claude/skills/summarize/SKILL.md`
Expected: 1 (the protocol is present)

Run: `grep -c "Synthesis_Rules" .claude/skills/summarize/SKILL.md`
Expected: 2 (opening and closing tags)

- [ ] **Step 3: Commit the SKILL.md rewrite**

```bash
git add .claude/skills/summarize/SKILL.md
git commit -m "refactor(summarize): inline summarize-agent synthesis logic into skill"
```

---

### Task 2: Delete summarize-agent.md

**Files:**
- Delete: `.claude/agents/summarize-agent.md`

- [ ] **Step 1: Verify no other files reference summarize-agent**

Run: `grep -r "summarize-agent" .claude/ docs/ --include="*.md" | grep -v "harness-v2-design" | grep -v "refactor-predev-inline-agent-design"`
Expected: 0 results (the SKILL.md reference was removed in Task 1; the harness-v2-design references are expected since it's the parent spec that planned this deletion)

- [ ] **Step 2: Delete the agent file**

```bash
git rm .claude/agents/summarize-agent.md
```

- [ ] **Step 3: Verify deletion**

Run: `ls .claude/agents/`
Expected: Only `study-agent.md` remains (or empty if other agents were already removed)

- [ ] **Step 4: Commit the deletion**

```bash
git commit -m "refactor(summarize): remove summarize-agent — logic merged into skill"
```

---

### Task 3: Final verification

- [ ] **Step 1: Verify no dangling references to summarize-agent**

Run: `grep -r "summarize-agent" . --include="*.md" | grep -v "harness-v2-design" | grep -v "refactor-predev-inline-agent-design" | grep -v ".git/"`
Expected: 0 results

- [ ] **Step 2: Verify skill structure is complete**

Run: `grep "^### Step" .claude/skills/summarize/SKILL.md`
Expected:
```
### Step 1: Load State
### Step 2: Collect Context
### Step 3: Synthesize Report
### Step 4: Present Summary
### Step 5: Update State
```

Run: `grep "^<\|^</" .claude/skills/summarize/SKILL.md`
Expected output includes all expected blocks:
- `<Purpose>` / `</Purpose>`
- `<Use_When>` / `</Use_When>`
- `<Do_Not_Use_When>` / `</Do_Not_Use_When>`
- `<Execution_Policy>` / `</Execution_Policy>`
- `<Steps>` / `</Steps>`
- `<Synthesis_Rules>` / `</Synthesis_Rules>`
- `<Tool_Usage>` / `</Tool_Usage>`
- `<Escalation>` / `</Escalation>`
- `<Final_Checklist>` / `</Final_Checklist>`

- [ ] **Step 3: Commit verification state if any fixes were needed**

Only if changes were made during verification.
