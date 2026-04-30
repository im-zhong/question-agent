---
name: pre-dev
description: Pre-development orchestrator — brainstorm, delegate, validate, and gate through spec → roadmap → toolchain
argument-hint: "<project description>"
triggers:
  - "pre-dev"
  - "pre dev"
  - "predev"
  - "pre-development"
  - "spec"
  - "write a spec"
  - "generate spec"
  - "PRD"
  - "roadmap"
  - "generate roadmap"
  - "功能树"
  - "功能拆分"
  - "toolchain"
  - "tech stack"
  - "技术栈"
  - "技术选型"
level: 4
---

<Purpose>
  承上启下。将 vague idea 或上一轮 summarize 报告转化为/更新开发材料，
  通过三个顺序阶段：spec (PRD) → roadmap (功能树) → toolchain (技术栈)。
  
  首次迭代：brainstorm → generate → validate → gate（完整三阶段）。
  后续迭代：加载 summarize 报告 → 评估变更 → 智能选择运行模式。
  
  每个阶段：brainstorm → generate → validate → gate。
  用户在每个门控点确认后再进入下一阶段。
</Purpose>

<Use_When>
  - 用户有项目想法，需要结构化 pre-dev 规划（首次迭代）
  - 完成一轮 dev-loop + summarize 后，需要更新设计并规划下一步（后续迭代）
  - 用户说 "pre-dev"、"pre dev"、"继续规划"、"下一步"、"更新设计"
  - Starting a new development cycle (pre-dev → progressive-plan → scaffold → dev → refactor → pre-dev)
</Use_When>

<Do_Not_Use_When>
  - User has a single bug fix or small change — skip planning
  - User wants autonomous execution — use autopilot or ralph
  - User wants a complete all-at-once plan — redirect to omc-plan
</Do_Not_Use_When>

<Execution_Policy>
  - Single skill that runs 3 sequential phases internally
  - Each phase: brainstorm → generate → validate → gate
  - Gates are NON-NEGOTIABLE: user MUST confirm before next phase
  - Brainstorm questions have NO upper limit — ask until the picture is clear
  - If a later phase reveals gaps, go back to the earlier phase (retaining clarified context)
</Execution_Policy>

<Steps>

### Phase 0: Iteration Assessment

pre-dev 的大脑。感知当前迭代状态，加载上下文，智能推荐运行模式。

**Step 0.1 — 加载状态**

读取 `docs/superpowers/state.md`：
- 存在 → 解析 frontmatter（iteration、current_phase、status）和文档快照表，提取 spec/roadmap/toolchain 路径
- 不存在 → 标记为"首次迭代"

**Step 0.2 — 收集迭代上下文（并行）**

同时执行：
- 加载 spec、roadmap、toolchain 文件（从 Step 0.1 文档快照路径）
- 搜索 `docs/superpowers/summaries/` 找最新 `*.md` 文件 → 加载全文
- `git log --oneline -10`

如果 summarize 报告不存在且非首次迭代（有 spec/roadmap），标注为"缺失 summarize"。

**Step 0.3 — 评估与推荐**

分析 4 个信号，计算推荐模式：

| 信号 | 来源 | 轻量刷新 ← | 增量更新 ← | 完整重跑 ← |
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
```

AskUserQuestion 选项：
- "<推荐模式> (Recommended)"
- "轻量刷新 — 只勾选完成项，跳过设计文档重新生成"
- "增量更新 — 局部调整 spec/roadmap/toolchain"
- "完整重跑 — 带上下文重新生成全部设计文档"

用户确认后，记录选定模式为 `$MODE`（`lightweight` / `incremental` / `full`），后续阶段据此调整行为。

### Phase 1: Spec

**Brainstorm — Requirement Clarification**

Check if the input is vague:
- Fewer than ~50 characters
- Missing goal, target user, or constraints
- No clear "who" and "why"

If vague, ask questions ONE AT A TIME using AskUserQuestion until the picture is clear:
- Start with: "Who is the target user? What do they need this for?"
- Follow with: "What's the core scenario? Walk me through the main use case."
- Then: "Are there any known constraints? (time, tech, domain, compliance)"
- Ask more if needed — no upper limit on questions

Stop when you can clearly state: goal + target user + 3+ key features.

If the input is already PRD-like, skip brainstorming and proceed to generate.

**Explore Project Context**

Gather context for the agent:
- Read CLAUDE.md, check pyproject.toml or package.json if present
- Note existing tech stack, project type, conventions
- Read existing spec file if in refine mode

**Generate**

Generate the spec document using Write. Follow this exact structure and constraints:

**Output Format:**

```markdown
# <Project Name> — Spec

**Created:** YYYY-MM-DD
**Last updated:** YYYY-MM-DD
**Status:** DRAFT

## Goal
<!-- 1-3 sentences. What problem does this solve? -->

## Target Users
<!-- Who will use this? -->

## Key Features
- [ ] <!-- feature 1 -->
- [ ] <!-- feature 2 -->
- [ ] <!-- feature 3 -->
<!-- max 5 features -->

## Non-Goals
<!-- What are we explicitly NOT building? -->

## Constraints
<!-- Known constraints: time, resources, technical, domain -->

## Unknowns
<!-- Must be non-empty. What we still need to figure out. -->
- <!-- unknown 1 -->
- <!-- unknown 2 -->

## Architecture

```mermaid
graph TB
    %% Simple architecture diagram. Start minimal, refine over iterations.
    %% Show system components and their relationships.
    %% Use dashed lines ( -.-> ) for planned/future components.
```

## Functional Hierarchy

```mermaid
graph TB
    %% Functional breakdown as a tree.
    %% Start simple — top-level domains only if early iteration.
    %% Add sub-functions as the design matures.
```
```

**Constraints:**
- Max 5 key features. Fewer is better.
- Unknowns field MUST be non-empty. Never claim certainty where it doesn't exist.
- No implementation details (no languages, frameworks, APIs, DB schemas).
- Architecture diagram: start with 3-6 nodes. Simple boxes and arrows.
- Functional hierarchy: top-level domains first. Add children in later iterations.
- If refining an existing spec: preserve what still applies, update what changed.
- Use mermaid `graph TB` for both diagrams.

**Examples:**

<Good>
  Goal: "Help teachers create and manage question banks for exams"
  Features: [question entry, category search, exam paper assembly] — 3 features, tight
  Unknowns: ["Whether multi-teacher collaboration is needed", "Question format scope"]
  Architecture: 4 nodes — User Browser, API Server, Question Store, File Storage
</Good>
<Bad>
  Features: [question CRUD, category management, search, filtering, sorting, pagination, bulk import, export, versioning, comments] — 10 features, over-designed
  Unknowns: [] — empty, pretending full clarity
  Architecture: 15 nodes with specific tech choices (PostgreSQL, Redis, S3) — implementation details
</Bad>

**Context for generation:**
- Mode: <initial | refine>
- Goal: <from brainstorming>
- Target users: <from brainstorming>
- Core features: <from brainstorming>
- Constraints: <from brainstorming>
- Existing spec (if refining): <content or 'N/A'>
- Project context: <exploration findings>

Output path: `docs/superpowers/specs/YYYY-MM-DD-<project-name>.md`

**Validate**

Read the spec file and check:
- [ ] Has all required sections: Goal, Target Users, Key Features, Non-Goals, Constraints, Unknowns
- [ ] Key features ≤ 5
- [ ] Unknowns is non-empty
- [ ] Architecture mermaid diagram present
- [ ] Functional hierarchy mermaid diagram present
- [ ] No implementation details (no language/framework/API references)

If validation fails, note the specific issues and re-generate with correction instructions.

**Gate Summary**

```
## Spec: <Project Name>

**Goal:** <one sentence>
**Target:** <who>
**Features:** <bullet list, max 5>
**Unknowns:** <bullet list>

📁 docs/superpowers/specs/YYYY-MM-DD-<name>.md

→ "Continue to roadmap?" or "What needs to change in the spec?"
```

**Gate Handling:**
- "Continue" → proceed to Phase 2
- "Change X" → re-generate with feedback (retain clarified requirements)
- "Skip for now" → mark spec status as DRAFT, proceed to Phase 2

### Phase 2: Roadmap

**Brainstorm — Functional Decomposition**

Read the spec file. Review its Key Features and Functional Hierarchy diagram.

Ask questions ONE AT A TIME using AskUserQuestion until the decomposition is clear:
- "Which features are independently shippable?"
- "What depends on what?"
- "What's the smallest set that delivers value? (minimum runnable system)"

No upper limit on questions. If the spec's functional hierarchy is already clear, skip brainstorming.

Also check if a roadmap already exists at `docs/superpowers/plans/*.md` with matching name.
If found → refine mode: read it to preserve checkbox states.

**Generate**

Generate the roadmap document using Write. Follow this exact structure and constraints:

**Output Format:**

```markdown
# <Project Name> — Roadmap

**Created:** YYYY-MM-DD
**Last updated:** YYYY-MM-DD

## 功能树

- [ ] <!-- Root: system/product name -->
  - [ ] <!-- Functional domain 1 -->
    - [ ] <!-- Specific function -->
    - [ ] <!-- Specific function -->
  - [ ] <!-- Functional domain 2 -->
    - [ ] <!-- Specific function -->
    - [ ] <!-- Specific function -->
      - [ ] <!-- Sub-function (max depth 4) -->
  - [ ] <!-- Functional domain 3 -->
    - [ ] <!-- Specific function -->
```

**Constraints:**
- PURE functional decomposition only. NO engineering tasks. Bad: "setup ruff", "init project", "configure CI", "write tests". Good: "题目格式校验", "全文搜索", "自动组卷规则".
- Max 4 levels deep (root → domain → function → sub-function).
- Each leaf node must be independently verifiable.
- Checkbox format: `- [ ]` on every node.
- The first functional domain should be the "minimum runnable system".
- Functional domains ordered by dependency.
- Names in the user's language (Chinese if spec is in Chinese).
- If refining: update checkbox statuses (`- [x]` for completed), add new features, restructure if needed.

**Examples:**

<Good>
```
- [ ] 题库系统/
  - [ ] 题目录入/
    - [ ] 单题录入
    - [ ] 批量导入
    - [ ] 题目格式校验
  - [ ] 分类检索/
    - [ ] 按知识点分类
    - [ ] 按难度筛选
    - [ ] 全文搜索
  - [ ] 试卷组卷/
    - [ ] 手动选题
    - [ ] 自动组卷规则
```
</Good>
<Bad>
```
- [ ] 题库系统/
  - [ ] 项目初始化
  - [ ] 配置 ruff 和 pytest
  - [ ] 搭建 FastAPI 框架
  - [ ] 题目CRUD API
```
Why bad: "项目初始化", "配置 ruff" are engineering tasks, not functional features.
</Bad>

**Context for generation:**
- Mode: <initial | refine>
- Spec content: <full spec markdown>
- Existing roadmap (if refining): <content or 'N/A'>

Output path: `docs/superpowers/plans/YYYY-MM-DD-<project-name>.md`

**Validate**

Read the roadmap file and check:
- [ ] All nodes use checkbox format (`- [ ]` or `- [x]`)
- [ ] No engineering tasks in leaf nodes (no "setup", "install", "configure", "init")
- [ ] Depth ≤ 4 levels
- [ ] First functional domain is minimum runnable system
- [ ] Functional domains ordered by dependency

Also detect existing function items:
```bash
ls docs/superpowers/items/*.md 2>/dev/null
```
For each items doc found, extract the functional point name. If a roadmap leaf node matches, convert the checkbox to a link:
```
Before: - [ ] 单题录入
After:  - [ ] [单题录入](items/2026-04-29-单题录入.md)
```
Detect progress markers from items doc status and update: 进行中 → `[~]`, 完成 → `[x]`.

If validation fails, re-generate with specific corrections.

**Gate Summary**

Show the functional tree in full:

```
## Roadmap: <Project Name>

- [ ] <系统名>/
  - [ ] <功能域1>/
    - [ ] <功能A>
    - [ ] <功能B>
  - [ ] <功能域2>/
    - [ ] <功能C>
    - [ ] <功能D>

📁 docs/superpowers/plans/YYYY-MM-DD-<name>.md

→ "Continue to toolchain?" or "What needs to change?"
```

**Gate Handling:**
- "Continue" → proceed to Phase 3
- "Change X" → re-generate with feedback
- "Skip" → proceed with DRAFT note

**回退:**
If the roadmap reveals gaps in the spec, return to Phase 1 to re-generate (retain clarified requirements, don't re-brainstorm from scratch).

### Phase 3: Toolchain

**Brainstorm + Research**

Read the spec and roadmap files. Run WebSearch for similar systems:

Search query pattern: `"<domain> tech stack" "build <system type>" lightweight architecture`
Run 2-3 WebSearch queries. Collect findings into a brief research summary.

Also check existing project tech stack:
```bash
cat pyproject.toml 2>/dev/null || cat package.json 2>/dev/null || echo "no existing project"
```

Ask user ONE question about tech preferences using AskUserQuestion:
- "Do you have tech stack preferences or constraints?" with options:
  - "No preference — recommend the simplest stack"
  - "Prefer Python ecosystem"
  - "Prefer TypeScript ecosystem"
  - "Must use specific tools (I'll specify)"

Then ask more if needed — no upper limit.

**Generate**

Generate the toolchain document using Write. Follow this exact structure and constraints:

**Output Format:**

```markdown
# <Project Name> — Toolchain

**Created:** YYYY-MM-DD
**Last updated:** YYYY-MM-DD
**Status:** DRAFT

## Phase 1 技术栈 (当前)

| 技术 | 支撑功能 | 选型理由 |
|------|---------|---------|
| <!-- tech --> | <!-- which roadmap functions this supports --> | <!-- why this choice --> |

## Phase 2+ 候选方向

| 阶段 | 候选技术 | 支撑功能 | 触发条件 |
|------|---------|---------|---------|
| Phase N | <!-- candidate tech --> | <!-- function it would support --> | <!-- when to consider it --> |

## 调研记录

| 来源 | 关键发现 |
|------|---------|
| websearch: "<query>" | <finding> |

## 风险 & 备选

- **风险:** <description> → **备选:** <alternative>
```

**Constraints:**
- Phase 1: CONFIRMED choices only. Each tech MUST map to a specific functional feature from the roadmap.
- Phase 2+: CANDIDATE only. Use tentative language: "可能使用", "候选", "待调研".
- Phase 3+: If the roadmap has more phases, mark as "开发时再定".
- Prefer simplicity. SQLite over PostgreSQL until you need concurrency. Local files over S3 until you need distribution. Single server over microservices until you have traffic.
- Every choice needs a one-sentence reason.
- Include at least 1 risk with alternative.
- Reuse existing project tech stack where possible.

**Examples:**

<Good>
Phase 1:
| FastAPI | 题目录入API、分类检索API | 项目已有Python基建，轻量异步框架 |
| SQLite | 题目存储、分类查询 | 单机轻量，Phase 1无并发需求 |

Phase 2+:
| Phase 2 | PostgreSQL + FTS | 全文搜索 | SQLite搜索性能不足时切换 |
</Good>
<Bad>
Phase 1:
| Kubernetes | 容器编排 | 为未来扩展做准备 |
| PostgreSQL | 主存储 | 生产环境标准 |
Why bad: K8s for Phase 1 is massive over-engineering. No function mapping.
</Bad>

**Context for generation:**
- Spec: <full spec markdown>
- Roadmap: <full roadmap markdown>
- WebSearch research: <search findings summary>
- User preferences: <preferences or 'no preference'>
- Existing project stack: <dependencies or 'greenfield'>

Output path: `.harness/<project-name>-toolchain.md`

**Validate**

Read the toolchain file and check:
- [ ] Phase 1 has concrete tech choices (not "待定")
- [ ] Each tech choice maps to a specific roadmap function
- [ ] Phase 2+ labeled as candidates ("候选", "可能", "待调研")
- [ ] At least 1 risk with alternative
- [ ] WebSearch findings recorded
- [ ] No massive over-engineering (no K8s for single-server apps, no microservices for Phase 1)

**Gate Summary**

```
## Toolchain: <Project Name>

**Phase 1 (当前):**
  <tech-1> ──→ <function-1>, <function-2>
  <tech-2> ──→ <function-3>

**Phase 2+ (候选):**
  <candidate-1> ──→ <future-function> (触发条件: <...>)

**风险:** <top risk>

📁 .harness/<name>-toolchain.md

→ "Confirm toolchain?" or "What needs to change?"
```

**Gate Handling:**
- "Confirm" → proceed to Summary
- "Change X" → re-generate with feedback
- "Skip" → mark DRAFT

**回退:**
If toolchain reveals missing roadmap functions, return to Phase 2 (or Phase 1) to re-generate.

### Phase 4: Final Summary

First, scan the roadmap to find the first available functional point:
- Read the roadmap file
- Find the first leaf node with `[ ]` status (not `[~]` or `[x]`)
- Use its name in the suggestion below

```
## Pre-Dev Complete

📋 Spec:    docs/superpowers/specs/<date>-<name>.md
🌲 Roadmap: docs/superpowers/plans/<date>-<name>.md
🔧 Stack:   .harness/<name>-toolchain.md

**建议下一步:**
  扫描 roadmap 中第一个无前置依赖的 `[ ]` 功能点
  → 运行 /progressive-plan 自动拆解

  或手动指定: /progressive-plan "<功能点名>"

All documents are living — they'll be refined in the next pre-dev cycle.
```

If any phase was skipped/DRAFT, add:
```
⚠️ 注意: <phase> 标记为 DRAFT，开发前请完善。
```

### Phase 5: Update State

全量流水线完成后，静默更新状态文件：

1. **state.md** (`docs/superpowers/state.md`):
   - 不存在 → 新建：iteration=1, current_phase=pre-dev, status=pre-dev
   - 存在 → 更新 frontmatter: current_phase=pre-dev, updated=<today>
   - 追加迭代索引行
   - 更新文档快照表

2. **迭代文件** (`docs/superpowers/iterations/NN-date.md`):
   - 不存在 → 新建：iteration=<N>, date_start=<today>, stages=[pre-dev]
   - 追加流程行：`| pre-dev | <date> | [spec](path), [roadmap](path), [toolchain](path) | ✅ |`

在 Final Summary 底部加一行：
```
状态已更新: docs/superpowers/state.md
```

</Steps>

<Tool_Usage>
  - Read: load spec, roadmap, existing project files
  - Bash: explore codebase, find matching files
  - AskUserQuestion: brainstorm at each phase (one at a time, no upper limit)
  - WebSearch: research similar system tech stacks (Phase 3)
  - Write: generate spec, roadmap, and toolchain documents
</Tool_Usage>

<Gate_Enforcement>
  Gates are NON-NEGOTIABLE. Every phase shows a summary, user confirms before next phase.
  The ONLY exception: user explicitly says "skip gates" or "auto-proceed".
</Gate_Enforcement>

<Escalation>
  - If document generation fails validation 3 times at the same phase, stop and ask user to provide direct input
  - If user says "this is taking too long, just give me the output", skip remaining gates
  - If user wants to stop after Phase 1 or 2, save what's done and suggest resuming later
</Escalation>

<Progressive_Principle>
  NEVER finalize tech for phases beyond the current one. "Phase 2+ 候选" is the correct
  level of detail. They will be decided when that phase's /pre-dev iteration runs.
</Progressive_Principle>
