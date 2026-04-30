# Pre-Dev 迭代感知 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 pre-dev 具备迭代感知能力 — 加载 summarize 报告，评估 4 信号，智能选择轻量刷新/增量更新/完整重跑模式。

**Architecture:** 单文件改动（`.claude/skills/pre-dev/SKILL.md`）。Phase 0 从简单文件查找升级为完整迭代评估入口；Phase 1-3 增加模式参数控制行为；Phase 4-5 按模式调整输出。

**Tech Stack:** Markdown skill definition, no code changes.

---

### Task 1: 重写 Purpose 和 Use_When 部分

**Files:**
- Modify: `.claude/skills/pre-dev/SKILL.md` (lines 25-42)

- [ ] **Step 1: 更新 Purpose 和 Use_When**

将 `<Purpose>` 块替换为：

```markdown
<Purpose>
  承上启下。将 vague idea 或上一轮 summarize 报告转化为/更新开发材料，
  通过三个顺序阶段：spec (PRD) → roadmap (功能树) → toolchain (技术栈)。
  
  首次迭代：brainstorm → generate → validate → gate（完整三阶段）。
  后续迭代：加载 summarize 报告 → 评估变更 → 智能选择运行模式。
  
  每个阶段：brainstorm → generate → validate → gate。
  用户在每个门控点确认后再进入下一阶段。
</Purpose>
```

将 `<Use_When>` 块更新为：

```markdown
<Use_When>
  - 用户有项目想法，需要结构化 pre-dev 规划（首次迭代）
  - 完成一轮 dev-loop + summarize 后，需要更新设计并规划下一步（后续迭代）
  - 用户说 "pre-dev"、"pre dev"、"继续规划"、"下一步"、"更新设计"
  - Starting a new development cycle (pre-dev → progressive-plan → scaffold → dev → refactor → pre-dev)
</Use_When>
```

- [ ] **Step 2: 验证改动**

```bash
grep -A 15 "<Purpose>" .claude/skills/pre-dev/SKILL.md
grep -A 8 "<Use_When>" .claude/skills/pre-dev/SKILL.md
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/pre-dev/SKILL.md
git commit -m "docs(pre-dev): update Purpose and Use_When for iteration awareness"
```

---

### Task 2: 重写 Phase 0 为 Iteration Assessment

**Files:**
- Modify: `.claude/skills/pre-dev/SKILL.md` (lines 52-58)

- [ ] **Step 1: 替换 Phase 0 内容**

将当前 Phase 0（lines 54-58）：

```markdown
### Phase 0: Setup

Determine mode:
- Search `docs/superpowers/specs/` for an existing spec matching the project name
- If found → refine mode (note what's changing, preserve what still applies)
- If not found → initial mode
```

替换为：

```markdown
### Phase 0: Iteration Assessment

pre-dev 的大脑。感知当前迭代状态，加载上下文，智能推荐运行模式。

**Step 0.1 — 加载状态**

读取 `docs/superpowers/state.md`：
- 存在 → 解析 frontmatter（iteration、current_phase、status）和文档快照表
- 不存在 → 标记为"首次迭代"
- 从文档快照获取 spec/roadmap/toolchain 路径

**Step 0.2 — 收集迭代上下文（并行）**

同时执行：
- 加载 spec、roadmap、toolchain 文件（从 Step 0.1 路径）
- 搜索 `docs/superpowers/summaries/` 找最新 `*.md` 文件 → 加载全文
- `git log --oneline -10`

如果 summarize 报告不存在且非首次迭代（有 spec/roadmap），标注为"缺失 summarize"。

**Step 0.3 — 评估与推荐**

分析 4 个信号，计算推荐模式：

| 信号 | 来源 | 轻量刷新 → | 增量更新 → | 完整重跑 → |
|------|------|-----------|-----------|-----------|
| 文档新旧 | spec/roadmap 更新时间 vs git log | 文档与最新 commit 同步 | 滞后 < 10 commits | 滞后 > 10 commits |
| 变更幅度 | summarize G 节或 git diff stat | +100 行以下，≤3 文件 | 中等 | +500 行以上，10+ 文件 |
| 遗留问题严重性 | summarize D 节 | 仅小修小补 | 功能未开始/集成未完成 | 架构级问题需重新设计 |
| 用户显式意图 | 用户输入 | "继续"/"下一步" | 无明确信号 | "重新设计"/"推倒重来"/"换框架" |

综合规则（优先级从高到低）：
1. 用户显式意图 → 直接决定（最高优先）
2. 架构级遗留问题 → 完整重跑
3. 文档严重滞后 + 大变更幅度 → 完整重跑
4. 文档同步 + 小变更幅度 + 无严重遗留 → 轻量刷新
5. 其他情况 → 增量更新（默认）
6. 缺失 summarize → 降级为完整重跑

**Step 0.4 — 用户确认**

展示评估摘要并使用 AskUserQuestion 让用户确认：

```
## 迭代评估 — Iteration <N>

📋 上一轮: <summarize 路径或 "首次迭代">
📊 变更: <X commits, +Y/-Z 行, W 文件 或 "首次迭代，无历史">
⚠️ 遗留: <N 个 或 "无">

→ 建议: **<模式>**
  理由: <2-3 句话解释判断依据>

选择模式:
```

AskUserQuestion 选项：
- "<推荐模式> (Recommended)"
- "轻量刷新 — 只勾选完成项，跳过设计文档"
- "增量更新 — 局部调整 spec/roadmap/toolchain"
- "完整重跑 — 带上下文重新生成全部设计文档"

用户确认后，记录选定模式为 `$MODE`（lightweight / incremental / full），后续阶段据此调整行为。
```

- [ ] **Step 2: 验证 Phase 0 结构完整**

```bash
grep -c "Step 0\.[1-4]" .claude/skills/pre-dev/SKILL.md
# Expected: 4
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/pre-dev/SKILL.md
git commit -m "refactor(pre-dev): rewrite Phase 0 as Iteration Assessment"
```

---

### Task 3: 更新 Phase 1 (Spec) 支持三种模式

**Files:**
- Modify: `.claude/skills/pre-dev/SKILL.md` (lines 61-206, Phase 1 section)

- [ ] **Step 1: 在 Phase 1 开头添加模式分支**

在 `### Phase 1: Spec` 标题后、`**Brainstorm**` 之前插入模式路由：

```markdown
### Phase 1: Spec

**Mode routing:**

- `$MODE == lightweight` → 跳过 Phase 1。Spec 不重新生成。
- `$MODE == incremental` → 下方 **增量更新** 路径
- `$MODE == full` → 下方 **完整重跑** 路径（当前流程 + summarize 上下文）

---

#### 增量更新路径

**加载与对比**

读取现有 spec 文件。加载 summarize 报告全文作为上下文。

检查以下变更点：
1. 架构图：summarize H 节（架构快照）与 spec 架构图是否一致。不一致 → 更新 spec 架构 mermaid 图
2. Unknowns：summarize D 节（遗留问题）是否有新的 unknown。有 → 追加到 Unknowns 列表
3. Key Features：summarize A 节（本轮完成）是否暗示需要新增/调整 feature
4. 更新 "Last updated" 日期

**展示 diff 摘要：**

```
## Spec 增量更新

无变化:
  - Goal: 保持不变
  - Target Users: 保持不变
  - Non-Goals: 保持不变
  - Constraints: 保持不变

改动:
  - Architecture 图: 新增 <组件名> 节点
  - Unknowns: 追加 "<新 unknown>"
  - Key Features: <功能X> 标记为完成

📁 docs/superpowers/specs/<date>-<name>.md
```

使用 AskUserQuestion 确认："Apply these spec changes?"

确认后使用 Edit 更新 spec 文件（不重新生成整个文件）。

---

#### 完整重跑路径
```

然后保留当前 Phase 1 的 Brainstorm → Generate → Validate → Gate 完整流程，但在 **Generate** 的 "Context for generation" 中加入：

```markdown
- Previous summarize report: <summarize content or 'N/A (首次迭代)'>
```

- [ ] **Step 2: 验证三种路径都有明确指令**

```bash
grep -n "Mode routing\|增量更新路径\|完整重跑路径" .claude/skills/pre-dev/SKILL.md
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/pre-dev/SKILL.md
git commit -m "feat(pre-dev): add mode-dependent behavior to Phase 1 (Spec)"
```

---

### Task 4: 更新 Phase 2 (Roadmap) 支持三种模式

**Files:**
- Modify: `.claude/skills/pre-dev/SKILL.md` (Phase 2 section)

- [ ] **Step 1: 在 Phase 2 开头添加模式路由**

在 `### Phase 2: Roadmap` 标题后插入：

```markdown
### Phase 2: Roadmap

**Mode routing:**

- `$MODE == lightweight` → 下方 **轻量刷新** 路径
- `$MODE == incremental` → 下方 **增量更新** 路径
- `$MODE == full` → 下方 **完整重跑** 路径

---

#### 轻量刷新路径

只做检测 + 勾选，不重新生成。

1. 读取 roadmap 文件
2. 读取 summarize A 节（本轮完成），提取已完成的功能名称
3. 在 roadmap 中将对应节点从 `- [ ]` 改为 `- [x]`
4. 检测 items 目录：
   ```bash
   ls docs/superpowers/items/*.md 2>/dev/null
   ```
   对每个 items doc，提取功能点名。如果 roadmap 叶子节点匹配 → 转为链接：`- [x] [功能名](items/<file>.md)`
5. 展示更新后的功能树：

```
## Roadmap 刷新

- [x] <系统名>/
  - [x] <功能域1>/
    - [x] [<功能A>](items/<file>.md)
    - [x] [<功能B>](items/<file>.md)
  - [ ] <功能域2>/
    - [ ] <功能C>

📁 docs/superpowers/plans/<date>-<name>.md

→ "Continue to toolchain?" or "Skip to summary?"
```

使用 Edit 更新 roadmap 文件中的 checkbox 状态。

---

#### 增量更新路径

1. 执行轻量刷新路径的勾选 + 链接步骤
2. 读取 summarize F 节（下一轮建议），检查是否有建议的新功能
3. 新功能追加到对应功能域下（不重排整个树）
4. 如果现有功能树结构不合理（如深度 > 4）→ 局部调整
5. 展示 diff 摘要，用户确认后 Edit 更新

---

#### 完整重跑路径
```

保留当前 Phase 2 的完整流程，在 **Generate** 的 "Context for generation" 中加入：

```markdown
- Previous summarize report: <summarize content or 'N/A'>
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/pre-dev/SKILL.md
git commit -m "feat(pre-dev): add mode-dependent behavior to Phase 2 (Roadmap)"
```

---

### Task 5: 更新 Phase 3 (Toolchain) 支持三种模式

**Files:**
- Modify: `.claude/skills/pre-dev/SKILL.md` (Phase 3 section)

- [ ] **Step 1: 在 Phase 3 开头添加模式路由**

```markdown
### Phase 3: Toolchain

**Mode routing:**

- `$MODE == lightweight` → 跳过 Phase 3。Toolchain 不重新生成。
- `$MODE == incremental` → 下方 **增量更新** 路径
- `$MODE == full` → 下方 **完整重跑** 路径

---

#### 增量更新路径

读取现有 toolchain + summarize 报告。检查以下追加点：

1. 外部知识：summarize E 节有新发现 → 追加到"调研记录"表格
2. 关键决策：summarize J 节影响技术选择 → 更新对应条目（追加新行或标注备选变更）
3. 经验教训：summarize K 节暴露新风险 → 追加到"风险 & 备选"

展示 diff 摘要：

```
## Toolchain 增量更新

无变化:
  - Phase 1 技术栈: 保持不变

追加:
  - 调研记录: +1 条（来源: summarize E 节）
  - 风险 & 备选: +1 条（来源: summarize K 节）

📁 .harness/<name>-toolchain.md
```

用户确认后 Edit 更新。

---

#### 完整重跑路径
```

保留当前 Phase 3 完整流程，在 **Generate** 的 "Context for generation" 中加入：

```markdown
- Previous summarize report: <summarize content or 'N/A'>
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/pre-dev/SKILL.md
git commit -m "feat(pre-dev): add mode-dependent behavior to Phase 3 (Toolchain)"
```

---

### Task 6: 更新 Phase 4 (Final Summary) 和 Phase 5

**Files:**
- Modify: `.claude/skills/pre-dev/SKILL.md` (Phase 4-5 sections)

- [ ] **Step 1: 更新 Phase 4 按模式调整输出**

将 Phase 4 的 Final Summary 部分替换为按模式分支的版本：

```markdown
### Phase 4: Final Summary

**轻量刷新模式：**

```
## Pre-Dev Complete (轻量刷新)

📋 上一轮总结: docs/superpowers/summaries/<date>-summary.md
🌲 下一个功能点: <roadmap 中第一个 [ ] 叶子节点>

**建议下一步:**
  运行 /progressive-plan "<功能点名>" 开始拆解
  或 /pre-dev "<描述>" 重新评估
```

**增量更新模式：**

```
## Pre-Dev Complete

📋 Spec:    docs/superpowers/specs/<date>-<name>.md （改动: <摘要>）
🌲 Roadmap: docs/superpowers/plans/<date>-<name>.md （改动: <摘要>）
🔧 Stack:   .harness/<name>-toolchain.md （改动: <摘要>）

**建议下一步:**
  扫描 roadmap 中第一个无前置依赖的 [ ] 功能点
  → 运行 /progressive-plan 自动拆解
```

**完整重跑模式：** 使用当前格式（不变）。

If any phase was skipped/DRAFT, add:
```
⚠️ 注意: <phase> 标记为 DRAFT，开发前请完善。
```
```

- [ ] **Step 2: 保留 Phase 5（不变）**

Phase 5: Update State 保持不变，所有模式都执行。

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/pre-dev/SKILL.md
git commit -m "refactor(pre-dev): update Phase 4-5 for mode-aware final summary"
```

---

### Task 7: 更新 Progressive_Principle 和 Escalation

**Files:**
- Modify: `.claude/skills/pre-dev/SKILL.md` (lines 544-548)

- [ ] **Step 1: 更新 Progressive_Principle**

替换：

```markdown
<Progressive_Principle>
  NEVER finalize tech for phases beyond the current one. "Phase 2+ 候选" is the correct
  level of detail. They will be decided when that phase's /pre-dev iteration runs.
  
  每次 pre-dev 迭代都是 refinement 机会：spec 从模糊到精确，roadmap 从粗到细，
  toolchain 从候选到锁定。summarize 报告是迭代间的桥梁 — 经验教训、遗留问题、
  外部知识通过它流入下一轮设计。
  
  轻量刷新和增量更新是常态，完整重跑是例外。
</Progressive_Principle>
```

- [ ] **Step 2: 更新 Escalation**

在 `<Escalation>` 块末尾追加：

```markdown
  - 如果 summarize 报告与当前文档严重冲突（如 spec 描述与架构快照完全不同），提示用户手动确认后再继续
  - 如果连续 2 次轻量刷新后用户仍不满意 → 建议升级到增量更新
  - 如果连续 2 次增量更新后用户仍不满意 → 建议升级到完整重跑
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/pre-dev/SKILL.md
git commit -m "docs(pre-dev): update Progressive_Principle and Escalation for iteration awareness"
```

---

### Task 8: 全文件一致性检查

**Files:**
- Check: `.claude/skills/pre-dev/SKILL.md`

- [ ] **Step 1: 结构完整性检查**

```bash
# 检查所有 Phase 标题存在
grep -n "^### Phase" .claude/skills/pre-dev/SKILL.md
# Expected: Phase 0, Phase 1, Phase 2, Phase 3, Phase 4, Phase 5

# 检查三种模式都出现
grep -c "轻量刷新" .claude/skills/pre-dev/SKILL.md
grep -c "增量更新" .claude/skills/pre-dev/SKILL.md
grep -c "完整重跑" .claude/skills/pre-dev/SKILL.md

# 检查 summarize 引用
grep -c "summarize" .claude/skills/pre-dev/SKILL.md
```

- [ ] **Step 2: 检查无矛盾指令**

通读文件，确认：
- Phase 0 中 `$MODE` 变量在 Phase 1-4 中被引用
- 轻量刷新模式在所有阶段行为一致（Phase 1 跳过，Phase 2 只勾选，Phase 3 跳过）
- 完整重跑行为与当前 pre-dev 向后兼容
- 没有残留的旧 Phase 0 逻辑（"initial mode / refine mode"）

- [ ] **Step 3: 最终 lint 检查**

```bash
# Markdown 结构检查：所有 code blocks 正确闭合
grep -c '```' .claude/skills/pre-dev/SKILL.md
# 应为偶数

# Frontmatter 完整性
head -23 .claude/skills/pre-dev/SKILL.md
```

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/pre-dev/SKILL.md
git commit -m "chore(pre-dev): final consistency pass for iteration awareness"
```
