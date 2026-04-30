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
  Transform a vague idea into development-ready materials through three sequential phases:
  spec (PRD) → roadmap (functional tree) → toolchain (tech stack).
  Each phase follows: brainstorm → delegate to pre-dev-agent → validate → gate.
  User confirms at each gate before proceeding.
</Purpose>

<Use_When>
  - User has a project idea and wants structured pre-development planning
  - Starting a new development cycle (pre-dev → progressive-plan → scaffold → dev → refactor → pre-dev)
  - User says "pre-dev", "pre dev", or describes wanting to plan before coding
</Use_When>

<Do_Not_Use_When>
  - User has a single bug fix or small change — skip planning
  - User wants autonomous execution — use autopilot or ralph
  - User wants a complete all-at-once plan — redirect to omc-plan
</Do_Not_Use_When>

<Execution_Policy>
  - Single skill that runs 3 sequential phases internally
  - Each phase: brainstorm → delegate pre-dev-agent → validate → gate
  - Gates are NON-NEGOTIABLE: user MUST confirm before next phase
  - Brainstorm questions have NO upper limit — ask until the picture is clear
  - If a later phase reveals gaps, go back to the earlier phase (retaining clarified context)
</Execution_Policy>

<Steps>

### Phase 0: Setup

Determine mode:
- Search `docs/superpowers/specs/` for an existing spec matching the project name
- If found → refine mode (note what's changing, preserve what still applies)
- If not found → initial mode

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

If the input is already PRD-like, skip brainstorming and proceed to delegate.

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
- "Change X" → re-delegate with feedback (retain clarified requirements)
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

**Delegate**

```
Agent(
  description: "Generate functional roadmap tree",
  subagent_type: "oh-my-claudecode:pre-dev-agent",
  model: "opus",
  prompt: "
    phase: roadmap
    Mode: <initial | refine>
    Spec content:
    <full spec markdown>

    Existing roadmap (if refining): <content or 'N/A'>

    Output path: docs/superpowers/plans/YYYY-MM-DD-<project-name>.md
    Write the roadmap to that path.
  "
)
```

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

If validation fails, re-delegate with specific corrections.

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
- "Change X" → re-delegate with feedback
- "Skip" → proceed with DRAFT note

**回退:**
If the roadmap reveals gaps in the spec, return to Phase 1 to re-delegate (retain clarified requirements, don't re-brainstorm from scratch).

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

**Delegate**

```
Agent(
  description: "Generate toolchain proposal",
  subagent_type: "oh-my-claudecode:pre-dev-agent",
  model: "opus",
  prompt: "
    phase: toolchain
    Spec:
    <full spec markdown>

    Roadmap:
    <full roadmap markdown>

    WebSearch research:
    <search findings summary>

    User preferences: <preferences or 'no preference'>
    Existing project stack: <dependencies or 'greenfield'>

    Output path: .harness/<project-name>-toolchain.md
    Write the toolchain doc to that path.
  "
)
```

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
- "Change X" → re-delegate with feedback
- "Skip" → mark DRAFT

**回退:**
If toolchain reveals missing roadmap functions, return to Phase 2 (or Phase 1) to re-delegate.

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
  - Agent: delegate to pre-dev-agent (model=opus, phase="spec"|"roadmap"|"toolchain")
  - Do NOT use Write or Edit — pre-dev-agent writes the files
</Tool_Usage>

<Gate_Enforcement>
  Gates are NON-NEGOTIABLE. Every phase shows a summary, user confirms before next phase.
  The ONLY exception: user explicitly says "skip gates" or "auto-proceed".
</Gate_Enforcement>

<Escalation>
  - If an agent delegation fails 3 times at the same phase, stop and ask user to provide direct input
  - If user says "this is taking too long, just give me the output", skip remaining gates
  - If user wants to stop after Phase 1 or 2, save what's done and suggest resuming later
</Escalation>

<Progressive_Principle>
  NEVER finalize tech for phases beyond the current one. "Phase 2+ 候选" is the correct
  level of detail. They will be decided when that phase's /pre-dev iteration runs.
</Progressive_Principle>
