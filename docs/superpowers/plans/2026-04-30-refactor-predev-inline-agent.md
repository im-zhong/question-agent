# Refactor pre-dev: Inline Agent into Skill — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the pre-dev-agent sub-agent by merging its document-generation logic directly into the pre-dev skill, preserving all functionality.

**Architecture:** Replace 3 Agent() delegate calls in the skill with direct Write-based document generation. The agent's output formats, constraints, and examples move inline into each phase's steps. Delete the agent file.

**Tech Stack:** Markdown skill definitions (no code)

---

### Task 1: Replace Phase 1 (Spec) Delegate with Generate

**Files:**
- Modify: `.claude/skills/pre-dev/SKILL.md`

- [ ] **Step 1: Replace the Phase 1 Delegate block with Generate block**

Find the **Delegate** section under Phase 1 (around line 87-110). It starts with:
```
**Delegate**

```
Agent(
  description: "Generate spec document",
  subagent_type: "oh-my-claudecode:pre-dev-agent",
  model: "opus",
  prompt: "
    phase: spec
    Mode: <initial | refine>
    ...
```

And the agent call block (the triple-backtick code block containing the Agent() call).

Replace the entire **Delegate** section with a **Generate** section:

```markdown
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

**Context for generation:**
- Mode: <initial | refine>
- Goal: <from brainstorming>
- Target users: <from brainstorming>
- Core features: <from brainstorming>
- Constraints: <from brainstorming>
- Existing spec (if refining): <content or 'N/A'>
- Project context: <exploration findings>

Output path: `docs/superpowers/specs/YYYY-MM-DD-<project-name>.md`
```

- [ ] **Step 2: Verify the replacement**

Read the file and confirm:
- The old Agent() call block is gone
- The new Generate block has output format, constraints, and context
- The output path is explicit

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/pre-dev/SKILL.md
git commit -m "refactor(pre-dev): inline Phase 1 spec generation, remove Agent call"
```

---

### Task 2: Replace Phase 2 (Roadmap) Delegate with Generate

**Files:**
- Modify: `.claude/skills/pre-dev/SKILL.md`

- [ ] **Step 1: Replace the Phase 2 Delegate block with Generate block**

Find the **Delegate** section under Phase 2 (around line 160-178). Replace it with:

```markdown
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

**Context for generation:**
- Mode: <initial | refine>
- Spec content: <full spec markdown>
- Existing roadmap (if refining): <content or 'N/A'>

Output path: `docs/superpowers/plans/YYYY-MM-DD-<project-name>.md`
```

- [ ] **Step 2: Verify the replacement**

Read the file and confirm:
- The old Agent() call block is gone
- The new Generate block has output format, constraints, and context
- The output path is explicit

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/pre-dev/SKILL.md
git commit -m "refactor(pre-dev): inline Phase 2 roadmap generation, remove Agent call"
```

---

### Task 3: Replace Phase 3 (Toolchain) Delegate with Generate

**Files:**
- Modify: `.claude/skills/pre-dev/SKILL.md`

- [ ] **Step 1: Replace the Phase 3 Delegate block with Generate block**

Find the **Delegate** section under Phase 3 (around line 256-278). Replace it with:

```markdown
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

**Context for generation:**
- Spec: <full spec markdown>
- Roadmap: <full roadmap markdown>
- WebSearch research: <search findings summary>
- User preferences: <preferences or 'no preference'>
- Existing project stack: <dependencies or 'greenfield'>

Output path: `.harness/<project-name>-toolchain.md`
```

- [ ] **Step 2: Verify the replacement**

Read the file and confirm:
- The old Agent() call block is gone
- The new Generate block has output format, constraints, and context
- The output path is explicit

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/pre-dev/SKILL.md
git commit -m "refactor(pre-dev): inline Phase 3 toolchain generation, remove Agent call"
```

---

### Task 4: Update Tool_Usage and Escalation sections

**Files:**
- Modify: `.claude/skills/pre-dev/SKILL.md`

- [ ] **Step 1: Update Tool_Usage section**

Find the `<Tool_Usage>` section (around line 367-374). Replace:

```markdown
<Tool_Usage>
  - Read: load spec, roadmap, existing project files
  - Bash: explore codebase, find matching files
  - AskUserQuestion: brainstorm at each phase (one at a time, no upper limit)
  - WebSearch: research similar system tech stacks (Phase 3)
  - Agent: delegate to pre-dev-agent (model=opus, phase="spec"|"roadmap"|"toolchain")
  - Do NOT use Write or Edit — pre-dev-agent writes the files
</Tool_Usage>
```

With:

```markdown
<Tool_Usage>
  - Read: load spec, roadmap, existing project files
  - Bash: explore codebase, find matching files
  - AskUserQuestion: brainstorm at each phase (one at a time, no upper limit)
  - WebSearch: research similar system tech stacks (Phase 3)
  - Write: generate spec, roadmap, and toolchain documents
</Tool_Usage>
```

- [ ] **Step 2: Update Escalation section**

Find the `<Escalation>` section (around line 381-385). Replace:

```markdown
<Escalation>
  - If an agent delegation fails 3 times at the same phase, stop and ask user to provide direct input
  - If user says "this is taking too long, just give me the output", skip remaining gates
  - If user wants to stop after Phase 1 or 2, save what's done and suggest resuming later
</Escalation>
```

With:

```markdown
<Escalation>
  - If document generation fails validation 3 times at the same phase, stop and ask user to provide direct input
  - If user says "this is taking too long, just give me the output", skip remaining gates
  - If user wants to stop after Phase 1 or 2, save what's done and suggest resuming later
</Escalation>
```

- [ ] **Step 3: Verify the changes**

Read the file and confirm:
- Tool_Usage no longer mentions Agent or "Do NOT use Write"
- Escalation says "generation fails validation" instead of "agent delegation fails"

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/pre-dev/SKILL.md
git commit -m "refactor(pre-dev): update Tool_Usage and Escalation for inline generation"
```

---

### Task 5: Delete pre-dev-agent.md

**Files:**
- Delete: `.claude/agents/pre-dev-agent.md`

- [ ] **Step 1: Delete the agent file**

```bash
rm .claude/agents/pre-dev-agent.md
```

- [ ] **Step 2: Verify the file is gone**

```bash
ls .claude/agents/pre-dev-agent.md 2>&1
```

Expected: "No such file or directory"

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/pre-dev-agent.md
git commit -m "refactor(pre-dev): delete pre-dev-agent, logic now inline in skill"
```

---

### Task 6: Final Verification

**Files:**
- Read: `.claude/skills/pre-dev/SKILL.md`

- [ ] **Step 1: Read the final skill file and verify completeness**

Read `.claude/skills/pre-dev/SKILL.md` and check:
- [ ] No remaining `Agent(` calls
- [ ] No remaining `subagent_type` references
- [ ] No remaining `pre-dev-agent` references
- [ ] All 3 phases have Generate blocks with output format, constraints, context, and output path
- [ ] Tool_Usage lists Write (not Agent)
- [ ] Escalation mentions "generation fails validation" (not "agent delegation fails")
- [ ] Phase 0 (Setup), Brainstorm steps, Validate steps, Gate steps, Phase 4 (Final Summary), Phase 5 (Update State) are all unchanged

- [ ] **Step 2: Verify the agent file is deleted**

```bash
ls .claude/agents/pre-dev-agent.md 2>&1
```

Expected: "No such file or directory"

- [ ] **Step 3: Final commit (if any cleanup needed)**

```bash
git status
```

If clean, no commit needed. If any stray changes, commit them.
