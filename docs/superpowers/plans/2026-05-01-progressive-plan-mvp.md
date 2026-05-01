# progressive-plan MVP/原型驱动 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Inject vertical-slice-first / prototype-driven principle into the progressive-plan skill, so function items are ordered for early end-to-end demo rather than layer-by-layer completion.

**Architecture:** Modify the single skill file `.claude/skills/progressive-plan/SKILL.md` with 7 targeted edits: update frontmatter + purpose, update reasoning process, add `原型` lifecycle tag, add `反馈` field to output template, update constraints, update examples, update validation checklist.

**Tech Stack:** Markdown skill definition (no executable code)

---

### Task 1: Update frontmatter description + Purpose

**Files:**
- Modify: `.claude/skills/progressive-plan/SKILL.md:1-18`

- [ ] **Step 1: Edit frontmatter description**

Change line 3 from:
```
description: Break a roadmap functional point into 5-7 executable function items — MUI strategy, lifecycle tags, behavior specs, system always runnable
```
to:
```
description: Break a roadmap functional point into 5-7 executable function items — MVP/prototype-driven vertical slices, lifecycle tags, feedback checkpoints, system always runnable
```

- [ ] **Step 2: Edit Purpose block**

Change lines 12-18 from:
```xml
<Purpose>
  Take a functional point from the pre-dev roadmap and break it down into 5-7 concrete function items.
  Each item is a Minimum Usable Increment — small enough for ~100-200 lines of code, large enough
  to be independently verifiable. The system stays runnable after every single item.

  This is the bridge between "what to build" (pre-dev spec/roadmap) and "how to build it step by step"
  (team-lead execution). Progressive disclosure: only one functional point at a time.
</Purpose>
```
to:
```xml
<Purpose>
  Take a functional point from the pre-dev roadmap and break it down into 5-7 concrete function items.
  Each item is a Minimum Usable Increment — small enough for ~100-200 lines of code, large enough
  to be independently verifiable. The system stays runnable after every single item.

  MVP/prototype-driven: when a functional point spans multiple layers, prioritize vertical slices
  that demonstrate end-to-end effects early. Use simplified/hardcoded logic to punch through layers,
  get feedback, then refine. Don't wait for a full layer to complete before starting the next.

  This is the bridge between "what to build" (pre-dev spec/roadmap) and "how to build it step by step"
  (team-lead execution). Progressive disclosure: only one functional point at a time.
</Purpose>
```

- [ ] **Step 3: Verify**

Read the file and confirm frontmatter line 3 and Purpose block are updated correctly.

---

### Task 2: Update Reasoning Process (Step 7)

**Files:**
- Modify: `.claude/skills/progressive-plan/SKILL.md:106-113`

- [ ] **Step 1: Replace Reasoning Process block**

Change lines 106-113 from:
```markdown
**Reasoning Process:**

1. Assess current code state — what already exists? What's missing?
2. Identify the smallest runnable first step — often a /health endpoint or equivalent skeleton.
3. Plan incremental capability additions — each F-N adds one new verifiable capability.
4. Identify stepping stones — what temporary code enables early verification but will be replaced?
5. Plan the cleanup — which function item removes temporary code?
6. Verify: after each F-N, can a developer run the system and verify it works?
```
to:
```markdown
**Reasoning Process:**

1. Assess current code state — what already exists? What's missing?
2. Identify the smallest runnable first step — often a /health endpoint or equivalent skeleton.
3. Identify end-to-end demo slice — from data input to user-visible output, what's the shortest path?
   Which modules need hardcoded/simplified logic to punch through?
4. Prioritize vertical slices — if the functional point spans multiple layers (data → processing → output),
   the first deliverable F-N should be a cross-layer prototype with simplified logic.
   Later F-Ns replace simplified parts with real implementations.
5. Plan incremental capability additions — after the prototype validates direction, add depth per-layer.
6. Identify stepping stones and prototype simplifications — temporary code that enables early verification.
7. Plan the cleanup — which function item removes temporary/simplified code?
8. Verify: after each F-N, can a developer run the system and verify it works?
```

- [ ] **Step 2: Verify**

Read lines 106-118 and confirm the new 8-step reasoning process is in place.

---

### Task 3: Update output format template — add `原型` lifecycle + `反馈` field

**Files:**
- Modify: `.claude/skills/progressive-plan/SKILL.md:131-149`

- [ ] **Step 1: Update F-1 template (lifecycle options)**

Change line 133 from:
```
- **生命周期:** 交付 | 过渡 | 重构
```
to:
```
- **生命周期:** 交付 | 过渡 | 原型 | 重构
```

- [ ] **Step 2: Update F-2+ template (lifecycle options + add 反馈 field)**

Change lines 141-149 from:
```markdown
### F-2: <name>
- [ ] **状态:** 待开始
- **生命周期:** 交付 | 过渡 | 重构
- **目标:** <!-- one sentence -->
- **验证:**
  - <!-- behavior spec 1 -->
- **依赖:** F-1
- **代码量:** ~<N> 行

<!-- ... F-3 through F-5/6/7 ... -->
```
to:
```markdown
### F-2: <name>
- [ ] **状态:** 待开始
- **生命周期:** 交付 | 过渡 | 原型 | 重构
- **目标:** <!-- one sentence -->
- **验证:**
  - <!-- behavior spec 1 -->
- **反馈:** <!-- 仅 原型 类型需要：完成后暂停，演示效果并评估什么？ -->
- **依赖:** F-1
- **代码量:** ~<N> 行

<!-- ... F-3 through F-5/6/7 ... -->
```

- [ ] **Step 3: Verify**

Read lines 131-150 and confirm both lifecycle tag lines show `交付 | 过渡 | 原型 | 重构` and F-2 template has the `反馈` field.

---

### Task 4: Update Constraints section — lifecycle tags + new constraints

**Files:**
- Modify: `.claude/skills/progressive-plan/SKILL.md:155-170`

- [ ] **Step 1: Update lifecycle tag definitions**

Change lines 159-165 from:
```markdown
- Lifecycle tags:
  - `交付` — final deliverable code, stays in the system
  - `过渡` — stepping stone, will be replaced by a later function item
  - `重构` — cleanup/refactor of temporary code from earlier items
- Status checkboxes: `- [ ]` 待开始, `- [x]` 已完成.
- Include at least one `过渡` item if the functional point requires incremental buildup (e.g., memory storage before SQLite).
- Include a `重构` item if prior stepping stones leave temporary code behind.
```
to:
```markdown
- Lifecycle tags:
  - `交付` — final deliverable code, stays in the system
  - `过渡` — stepping stone within one layer, will be replaced by a later function item
  - `原型` — cross-layer vertical slice with simplified logic, punches through multiple layers for early end-to-end demo. Must include a `反馈` field.
  - `重构` — cleanup/refactor of temporary code from earlier items
- Status checkboxes: `- [ ]` 待开始, `- [x]` 已完成.
- Include at least one `过渡` item if the functional point requires incremental buildup (e.g., memory storage before SQLite).
- Include a `原型` item if the functional point spans 2+ layers. Place it early (F-2 or F-3).
- Every `原型` item must include a `反馈` field specifying what to evaluate after demo.
- Include a `重构` item if prior stepping stones or prototypes leave temporary code behind.
```

- [ ] **Step 2: Verify**

Read lines 155-170 and confirm 4 lifecycle tags defined, `原型` has `反馈` requirement, and 3 constraint lines about `原型` are present.

---

### Task 5: Update Good/Bad examples

**Files:**
- Modify: `.claude/skills/progressive-plan/SKILL.md:173-193`

- [ ] **Step 1: Replace Good example with prototype-driven example**

Change lines 175-186 from:
```markdown
<Good>
Functional point: "单题录入" (current state: empty FastAPI project)

F-1: [ ] API 服务骨架 (交付) — /health endpoint, ~50行
F-2: [ ] 题目创建端点 / 内存存储 (过渡) — POST/GET, ~120行
F-3: [ ] 输入校验 (交付) — 422 errors, ~80行
F-4: [ ] SQLite 持久化 (交付) — replaces memory, ~100行
F-5: [ ] 题目模型完善 (交付) — full fields, ~130行
F-6: [ ] 代码清理 (重构) — remove memory store traces, ~60行

Why good: starts with /health skeleton, increments one capability at a time,
explicitly replaces temporary code, ends with cleanup. System runs after each step.
</Good>
```
to:
```markdown
<Good>
Functional point: "单题录入" (current state: empty FastAPI project)

F-1: [ ] API 服务骨架 (交付) — /health endpoint, ~50行
F-2: [ ] 题目创建端点 / 内存存储 (过渡) — POST/GET, ~120行
F-3: [ ] 输入校验 (交付) — 422 errors, ~80行
F-4: [ ] SQLite 持久化 (交付) — replaces memory, ~100行
F-5: [ ] 题目模型完善 (交付) — full fields, ~130行
F-6: [ ] 代码清理 (重构) — remove memory store traces, ~60行

Why good: starts with /health skeleton, increments one capability at a time,
explicitly replaces temporary code, ends with cleanup. System runs after each step.
</Good>

<Good>
Functional point: "题目生成" (current state: knowledge extraction done, no question generation)

F-1: [ ] 题目数据模型 + API 骨架 (交付) — Question model, POST /generate, ~80行
F-2: [ ] 端到端出题原型 (原型) — 硬编码知识点→简化GLM出题→返回题目, ~150行
  反馈: 🔄 完成后暂停，演示出题效果并评估：题目质量可接受？知识点粒度合适？
F-3: [ ] 知识点对接 (交付) — 从/knowledge获取真实知识点, ~100行
F-4: [ ] 题型扩展 (交付) — 选择题/填空题/简答题, ~120行
F-5: [ ] 难度控制 (交付) — 难度参数调节, ~80行
F-6: [ ] 清理硬编码 (重构) — 移除原型中的硬编码知识点, ~60行

Why good: F-2 is a cross-layer prototype that demos end-to-end early.
Feedback checkpoint after F-2 validates direction before investing in depth.
Subsequent F-Ns replace simplified logic with real implementations.
</Good>
```

- [ ] **Step 2: Replace Bad example with prototype-ignoring example**

Change lines 187-193 from:
```markdown
<Bad>
F-1: 实现完整的 CRUD API — 500行, too big
F-2: 写单元测试 — not a functional increment, testing is part of each step
F-3: 配置 CI/CD — engineering task, not functional

Why bad: F-1 is too large. "写测试" and "配置CI" are engineering tasks, not functional increments.
</Bad>
```
to:
```markdown
<Bad>
F-1: 实现完整的 CRUD API — 500行, too big
F-2: 写单元测试 — not a functional increment, testing is part of each step
F-3: 配置 CI/CD — engineering task, not functional

Why bad: F-1 is too large. "写测试" and "配置CI" are engineering tasks, not functional increments.
</Bad>

<Bad>
Functional point: "题目生成" (multi-layer, but broken down layer-by-layer)

F-1: 知识点模型定义 (交付) — single layer, no end-to-end path
F-2: 知识点提取逻辑 (交付) — single layer, no question output visible
F-3: 知识点存储 (交付) — single layer, pure infrastructure
F-4: 知识点层级构建 (交付) — single layer, still no question output
F-5: 知识点API (交付) — single layer, user cannot perceive output

Why bad: all items are single-layer horizontal slices. After F-5, still no demo-able effect.
No vertical slice, feedback loop delayed until the entire bottom layer is complete.
Should have a 原型 item punching through from knowledge to question output.
</Bad>
```

- [ ] **Step 3: Verify**

Read lines 173-210 and confirm both Good examples and both Bad examples are present with `原型` content.

---

### Task 6: Update Step 8 validation checklist

**Files:**
- Modify: `.claude/skills/progressive-plan/SKILL.md:209-215`

- [ ] **Step 1: Update validation checklist**

Change lines 209-215 from:
```markdown
- [ ] 5-7 function items
- [ ] Each has a lifecycle tag (交付 | 过渡 | 重构)
- [ ] Each has 1-3 behavioral verification specs (no CLI commands)
- [ ] Dependencies described in plain text (no JSON)
- [ ] Document ≤ 200 lines (excluding mermaid blocks)
- [ ] First item creates a runnable skeleton (e.g., /health)
- [ ] Includes at least one 过渡 item if buildup is needed
- [ ] Includes 重构 item if stepping stones leave temporary code
```
to:
```markdown
- [ ] 5-7 function items
- [ ] Each has a lifecycle tag (交付 | 过渡 | 原型 | 重构)
- [ ] Each has 1-3 behavioral verification specs (no CLI commands)
- [ ] Dependencies described in plain text (no JSON)
- [ ] Document ≤ 200 lines (excluding mermaid blocks)
- [ ] First item creates a runnable skeleton (e.g., /health)
- [ ] Includes at least one 过渡 item if buildup is needed
- [ ] If functional point spans 2+ layers, includes at least one 原型 item (placed at F-2 or F-3)
- [ ] Every 原型 item has a 反馈 field
- [ ] Includes 重构 item if stepping stones or prototypes leave temporary code
```

- [ ] **Step 2: Verify**

Read lines 207-218 and confirm 10 checklist items including the 3 new `原型`-related checks.

---

### Task 7: Update Step 10 Gate Summary example

**Files:**
- Modify: `.claude/skills/progressive-plan/SKILL.md:229-245`

- [ ] **Step 1: Update gate summary to show 原型 + 反馈**

Change lines 232-240 from:
```
  F-1: <name> (交付) → /health 返回 200
  F-2: <name> (过渡) → POST 创建、GET 查询
  F-3: <name> (交付) → 422 校验错误
  F-4: <name> (交付) → SQLite 持久化
  F-5: <name> (交付) → 完整字段
  F-6: <name> (重构) → 清理内存存储残留
```
to:
```
  F-1: <name> (交付) → /health 返回 200
  F-2: <name> (原型) → 端到端出题原型 🔄 反馈:评估出题效果
  F-3: <name> (交付) → 知识点对接
  F-4: <name> (交付) → 题型扩展
  F-5: <name> (交付) → 难度控制
  F-6: <name> (重构) → 清理硬编码
```

- [ ] **Step 2: Verify**

Read lines 229-245 and confirm the gate summary shows `原型` with 🔄 反馈 notation.

---

### Task 8: Commit

- [ ] **Step 1: Stage and commit**

```bash
git add .claude/skills/progressive-plan/SKILL.md
git commit -m "feat(progressive-plan): add MVP/prototype-driven vertical-slice principle

Add 原型 lifecycle tag for cross-layer end-to-end prototypes.
Add 反馈 field for feedback checkpoints after prototypes.
Update reasoning process to prioritize vertical slices.
Update constraints, examples, and validation checklist."
```

- [ ] **Step 2: Verify**

Run `git log --oneline -1` and confirm the commit message is correct.
