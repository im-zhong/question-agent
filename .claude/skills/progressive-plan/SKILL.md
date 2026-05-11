---
name: progressive-plan
description: Break a roadmap functional point into 5-7 executable function items — MVP-priority selection across branches, prototype-driven vertical slices, lifecycle tags, feedback checkpoints, system always runnable
argument-hint: "[functional point name | 'done' | empty to auto-find next]"
triggers:
  - "progressive plan"
  - "progressive-plan"
level: 4
---

<Purpose>
  Take a functional point from the pre-dev roadmap and break it down into 5-7 concrete function items.
  Each item is a Minimum Usable Increment — small enough for ~100-200 lines of code, large enough
  to be independently verifiable. The system stays runnable after every single item.

  MVP/prototype-driven at TWO levels:
  1. **Which functional point to pick next** — prioritize the leaf that, combined with completed work,
     creates the most demo-able end-to-end experience. Don't complete an entire branch before
     touching the next; punch across branches for early value.
  2. **How to break it down** — when a functional point spans multiple layers, prioritize vertical slices
     that demonstrate end-to-end effects early. Use simplified/hardcoded logic to punch through layers,
     get feedback, then refine.

  This is the bridge between "what to build" (pre-dev spec/roadmap) and "how to build it step by step"
  (dev-loop execution). Progressive disclosure: only one functional point at a time.
</Purpose>

<Use_When>
  - After pre-dev completes, user wants to start building
  - User wants to break down the next functional point from the roadmap
  - User says "/progressive-plan" or "progressive plan"
  - A functional point is complete and user wants to move to the next one
</Use_When>

<Do_Not_Use_When>
  - No pre-dev outputs exist — run /pre-dev first
  - User wants the full project plan at once — redirect to spec/roadmap documents
  - User wants to execute code — use dev-loop after progressive-plan
  - Single bug fix or trivial change — skip planning
</Do_Not_Use_When>

<Execution_Policy>
  - Skill orchestrates — it does NOT do the breakdown itself
  - Pre: read all inputs, explore codebase, find next functional point, confirm with user
  - Core: generate function items directly using Write
  - Post: validate output, write items doc, update roadmap link, gate
  - Never writes code. Only plans.
</Execution_Policy>

<Steps>

### Step 1: Gather Inputs

Read all pre-dev outputs:
```bash
ls docs/superpowers/specs/*.md docs/superpowers/plans/*.md .harness/*-toolchain.md
```

Read each file fully. If any missing, tell user: "Run /pre-dev first to generate spec, roadmap, and toolchain."

### Step 2: Check Codebase State

```bash
git log --oneline -5
ls -la src/ 2>/dev/null || ls -la *.py 2>/dev/null || echo "no source yet"
ls docs/superpowers/items/ 2>/dev/null || echo "no items yet"
```

Note: what already exists, what's been completed, what items have been broken down.

### Step 3: Determine Mode

| Input | Mode |
|-------|------|
| No args or "next" | **Auto-find**: scan roadmap for next available functional point |
| "done" | **Complete**: mark current `[~]` as `[x]`, then auto-find next |
| `<functional point name>` | **Specify**: user names a specific point to break down |

### Step 4: Find Next Available Functional Point (Auto-find Mode)

Scan the roadmap tree for ALL available leaf nodes — those that:
1. Have status `[ ]` (not started, not in progress, not completed)
2. Have all prerequisite leaf nodes within the same parent already `[x]` completed
3. Do NOT already have a link to an items/ document (not already broken down)

Among candidates, apply **MVP priority** scoring (not tree order):

| 优先级 | 维度 | 说明 |
|--------|------|------|
| 1 (最高) | 端到端可演示性 | 该 leaf 能否与已完成的工作组成端到端用户可感知的 demo？跨越分支的 leaf 优先（如"题目生成"比同分支的"知识点层级"更有演示价值） |
| 2 | 用户可见输出 | 该 leaf 是否直接产生目标用户可看到/评估的输出？ |
| 3 | 已有工作可复用 | 已完成的 leaf 越能支撑该 leaf，分越高（如"题目生成"可复用已完成的"知识点识别"） |
| 4 (tiebreaker) | 树序 | 同分时按 depth-first, top-to-bottom 排列 |

Present **top 2-3 candidates** to the user with MVP reasoning:
```
**候选功能点:**

1. 🎯 「基于知识点生成题干」(题目生成/基础出题)
   → MVP 优先: 已有知识点标注，可端到端 demo "教材→知识点→题目"
2. 「知识点层级关系构建」(教材知识抽取/知识点层级提取)
   → 树序优先: 同分支下一个 leaf

建议拆哪个？
```
Use AskUserQuestion with options derived from the ranked candidates.

### Step 5: Confirm Target Functional Point

If user specified a point or auto-find found one:
1. Confirm it's in the roadmap (it must exist as a leaf node)
2. Confirm it's not already `[x]` completed
3. Confirm it's not already `[~]` in progress (unless user wants to re-breakdown)

If the point has an existing items/ doc, ask: "Already has a breakdown. Re-do or view existing?"

### Step 6: Mark Roadmap In Progress

Update the roadmap file: change `- [ ] <point>` to `- [~] <point>`.
If the point already has an items link, preserve it: `- [~] [<point>](items/<name>.md)`.

### Step 7: Generate Function Items

Generate the function items document using Write. Follow this exact structure and constraints:

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

**Output Format:**

```markdown
# 功能项：<functional-point-name>

**来源:** [roadmap](../../docs/superpowers/plans/<date>-<project>.md)
**创建:** YYYY-MM-DD
**状态:** 进行中

## 拆解思路

<!-- 3-5 sentences. Current code state → starting point → why this breakdown order.
     Mention: what's the smallest runnable step? What are the stepping stones?
     What's the final deliverable? -->

## 功能项

### F-1: <name>
- [ ] **状态:** 待开始
- **生命周期:** 交付 | 过渡 | 原型 | 重构
- **目标:** <!-- one sentence -->
- **验证:**
  - <!-- behavior spec 1 -->
  - <!-- behavior spec 2 -->
- **依赖:** 无 | F-<N>
- **代码量:** ~<N> 行

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

**Constraints:**
- 5-7 function items total. Not 4, not 8.
- Document ≤ 200 lines (excluding mermaid code blocks).
- Each function item ~100-200 lines of code. Don't create 500-line items.
- Verification specs are BEHAVIOR descriptions, not CLI commands. "GET /health returns 200" not "curl localhost:8000/health".
- Each 交付 item's verification specs should include a walkthrough test expectation: "tests/integration/test_walkthrough.py covers POST /endpoint" or similar. The run skill will enforce this in Step 6b.
- Dependencies described in plain text ("依赖 F-1 的 API 骨架"), not JSON DAG.
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
- Order matters: F-1 → F-2 → ... → F-N is the execution order.
- Use mermaid diagrams ONLY when they add clarity beyond text (data flow, sequence, state). Don't force diagrams.
- Start from the CURRENT codebase state, not an idealized starting point.
- If a /health endpoint or project skeleton already exists, F-1 should build on it.
- Prefer smaller steps when in doubt. A 50-line step that works > a 200-line step that might compile.

**Examples:**

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

**Context for generation:**
- Target functional point: <name from Step 5>
- Spec: <full spec markdown>
- Roadmap: <full roadmap markdown>
- Toolchain: <full toolchain markdown>
- Codebase state: <git log, directory structure, existing items>
- Existing items docs: <list of related items/ files if any>

Output path: `docs/superpowers/items/YYYY-MM-DD-<point-name>.md`

### Step 8: Validate Output

Read the generated output and check:
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

If validation fails, note specific issues and re-generate with corrections.

### Step 9: Write and Link

1. Ensure `docs/superpowers/items/` directory exists
2. The file was written in Step 7 — verify it's at the expected path
3. Update roadmap: `- [~] <point>` → `- [~] [<point>](items/<date>-<point>.md)`

### Step 10: Gate Summary

Present a compact summary:

```
## 功能项拆解: <functional point>

**拆解思路:** <one sentence from the doc>

**功能项:**
  F-1: <name> (交付) → /health 返回 200
  F-2: <name> (原型) → 端到端出题原型 🔄 反馈:评估出题效果
  F-3: <name> (交付) → 知识点对接
  F-4: <name> (交付) → 题型扩展
  F-5: <name> (交付) → 难度控制
  F-6: <name> (重构) → 清理硬编码

📁 docs/superpowers/items/YYYY-MM-DD-<name>.md

→ "确认？开始 dev-loop 执行？" / "哪个功能项要改？"
```

Never dump the full document. The user can read the file.

### Step 11: Handle Gate

- Confirm → done. Suggest: "Ready for dev-loop. Run /dev-loop with this items doc."
- Change F-N → re-generate with specific feedback
- Skip → leave DRAFT status

</Steps>

<Tool_Usage>
  - Read: load spec, roadmap, toolchain, existing items docs
  - Bash: explore codebase, git log, directory listing
  - AskUserQuestion: confirm target functional point (show roadmap candidates)
  - Write: generate the function items document (Step 7)
  - Edit: update roadmap checkbox and link
</Tool_Usage>

<Progressive_Principle>
  ONE functional point at a time. Never break down multiple points in one invocation.
  Each function item keeps the system runnable. Progressive disclosure of complexity
  to the human — they see 5-7 items, not 50.
</Progressive_Principle>

<Gate_Behavior>
  Show function item list as gate summary. User confirms before dev-loop execution.
</Gate_Behavior>

<Escalation>
  - If generation fails validation 3 times on same point, present the roadblock and ask user for direct breakdown
  - If user says "just tell me what to build", redirect to dev-loop with the items doc
  - If no functional points left to break down, celebrate and suggest /pre-dev for next cycle
</Escalation>
