# Refactor: Summarize Inline Agent — Design

**Created:** 2026-05-01
**Last updated:** 2026-05-01
**Status:** CONFIRMED

## Goal

将 summarize-agent 的合成逻辑合并进 summarize skill，使 summarize 成为纯 skill（不委托 subagent）。不改变任何功能 — 输入、输出、报告格式、质量标准全部保持等价。

## Motivation

Harness V2 设计（`docs/superpowers/specs/2026-04-30-harness-v2-design.md`）明确指出：文档生成类 agent 应消除，逻辑融合进 skill。summarize-agent 只做合成，不做文件 I/O，适合内联。合并后减少一层间接调用，简化维护。

## Functional Equivalence

| 维度 | 合并前 | 合并后 |
|------|--------|--------|
| 输入 | spec + roadmap + toolchain + items + git log + diff + pytest + web search | 完全相同 |
| 输出 | 10-section 报告 markdown，≤ 200 行 | 完全相同 |
| 质量标准 | Success_Criteria、Constraints、Failure_Modes | 完全相同 |
| 执行位置 | Task() 隔离子代理上下文 | 主 session 上下文 |
| 文件写入 | skill 写入（agent 只输出 markdown） | 完全相同 |

## File Changes

### Modified

- `.claude/skills/summarize/SKILL.md` — 重写 Step 3，内联合成逻辑

### Deleted

- `.claude/agents/summarize-agent.md` — 逻辑已合并进 skill

### Unchanged

- `docs/superpowers/specs/2026-04-30-harness-v2-design.md` — 已规划此重构
- 其他 skill/agent 文件

## SKILL.md Structure

合并后的 SKILL.md 结构：

```
frontmatter
Purpose
Use_When
Do_Not_Use_When
Execution_Policy
Steps (1-5, Step 3 改为合成)
  Step 1: Load State (不变)
  Step 2: Collect Context (不变)
  Step 3: Synthesize Report (新)
    - 上下文说明（从 agent 的 Role + Why_This_Matters 提炼）
    - Synthesis_Protocol（7 步，从 agent 搬运）
    - Output_Format（合并 skill 和 agent 两处）
  Step 4: Present Summary (不变)
  Step 5: Update State (不变)
Synthesis_Rules (新块)
  Success_Criteria (从 agent 搬运)
  Constraints (从 agent 搬运)
  Section_Guidance (从 agent 搬运，10 个 section)
  Failure_Modes_To_Avoid (从 agent 搬运)
Tool_Usage (更新：移除 Task 行)
Escalation (更新：移除 agent 相关)
Final_Checklist (合并：补充 agent 特有的检查项)
```

## Step 3: Synthesize Report

取代原来的 "Delegate to summarize-agent"。skill 收集完 context 后，直接执行合成。

### 上下文说明

从 agent 的 `<Role>` 和 `<Why_This_Matters>` 提炼为 Step 3 的开头说明：
- 这一步在做什么：将本轮 dev 产出的代码、文档和 web search 知识合成为一份结构化总结报告
- 为什么重要：没有刻意总结，每个 pre-dev 周期就会盲目开始，重新发现分散在 repo 中的上下文

### Synthesis Protocol

从 agent 搬运的 7 步流程：
1. Absorb inputs — 读取所有提供的上下文
2. Cross-reference — 对比 git diff/log 与 spec/roadmap，标注偏差
3. Extract decisions — 扫描 git log 和 diff 提炼架构决策
4. Categorize findings — 事实 → A/B/C/G/H，判断 → D/E/F/J/K
5. Draft report — 写所有 section，空 section 说明原因
6. Trim to 200 lines — 削弱冗余，保留具体
7. Self-check — 扫描捏造，每项声明可溯源到输入

### Output Format

合并 skill 和 agent 两处的格式定义为一份。10-section 报告 + frontmatter，≤ 200 行文本（mermaid 除外）。

## Synthesis_Rules Block

### Success_Criteria

- 全部 10 section 存在且有实质内容（无 TBD 占位）
- "承上" sections (A/B/C/G/H) 基于实际代码 diff、git log、test output
- "启下" sections (D/E/F/J/K) 可操作 — 具体建议带理由
- 报告 ≤ 200 行文本（mermaid 除外）
- 事实与判断清晰区分
- 每个判断/建议有可见的推理链路回到输入证据

### Constraints

- 不捏造 — 输入缺失时明确标注，不猜测
- 架构图必须标注本轮改动（mermaid style 或颜色注释）
- 外部知识（E section）必须引用来源 — 域名或论文标题，非原始 URL

### Section_Guidance

10 个 section 的完整指导，从 agent 原样搬运：

- A. 本轮完成 — 功能级别，3-8 条，对比 spec/roadmap 标注偏差
- B. 代码变更 — diff stat 表格 + 关键变化意图说明，Top 5-8 文件
- C. 文档现状 — 文档类型/路径/状态表格，标注过期文档
- D. 遗留问题 — 带上下文的 bullet list，区分"延迟"和"不确定"
- E. 外部知识 — 可操作洞察，3-5 条，web search 失败则标注
- F. 下一轮建议 — 按优先级排序，"优先做 X，因为 Y"，基于 D+E+K
- G. 量化统计 — commits/文件/行数/测试通过率表格
- H. 架构快照 — mermaid 图，≤ 10 节点，标注本轮改动
- J. 关键决策 — ADR-lite：决定/原因/后果，1-3 条
- K. 经验教训 — ✅ 顺利 / ⚠️ 困难 / 💡 意外，各 2-3 条

### Failure_Modes_To_Avoid

- 重复 spec — 列做了什么，不列计划什么
- 空泛建议 — "继续完善功能" 无用，"优先实现自动组卷算法，因为手动选题已是瓶颈" 有用
- 捏造决策 — diff 中找不到就不发明
- 过详架构图 — ≤ 10 节点
- 忽略测试失败 — D 必须包含，F 必须应对
- 冗长教训 — 每类 2-3 条
- 浅薄外部知识 — 必须是具体洞察

## Tool_Usage Changes

移除：
```
- Task(subagent_type="oh-my-claudecode:summarize-agent", model="opus"): 委托报告合成
```

保留所有其他工具：Read、Bash、WebSearch、Write。

## Escalation Changes

- "summarize-agent 生成超 300 行 → 要求精简" → "报告超 200 行时自检精简再写入"
- 其他 escalation 规则不变

## Final_Checklist Changes

- "summarize-agent 委托完成并返回报告" → "报告合成完成"
- 补充 agent 特有的检查项：
  - 全部 10 section 存在
  - 事实可溯源到输入
  - 判断有推理依据
  - 架构图标注改动
  - 建议具体且按优先级排序
  - ≤ 200 行文本
  - 无捏造、无占位 section
