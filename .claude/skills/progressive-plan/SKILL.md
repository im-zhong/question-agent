---
name: progressive-plan
description: Break a roadmap functional point into 5-7 executable function items — MUI strategy, lifecycle tags, behavior specs, system always runnable
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

  This is the bridge between "what to build" (pre-dev spec/roadmap) and "how to build it step by step"
  (team-lead execution). Progressive disclosure: only one functional point at a time.
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
  - User wants to execute code — use team-lead after progressive-plan
  - Single bug fix or trivial change — skip planning
</Do_Not_Use_When>

<Execution_Policy>
  - Skill orchestrates — it does NOT do the breakdown itself
  - Pre: read all inputs, explore codebase, find next functional point, confirm with user
  - Core: delegate to progressive-planner agent for breakdown reasoning
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

Scan the roadmap tree. The next available point is the first leaf node that:
1. Has status `[ ]` (not started, not in progress, not completed)
2. All its dependencies (parent/prior siblings) are `[x]` or don't block it
3. Does NOT already have a link to an items/ document (not already broken down)

Priority: depth-first, top-to-bottom in the tree.

If multiple candidates, pick the first. Present to user:
```
**建议下一步:** 「单题录入」(Phase 1, 无前置依赖)
  拆这个功能点？
```
Use AskUserQuestion with options derived from the roadmap candidates.

### Step 5: Confirm Target Functional Point

If user specified a point or auto-find found one:
1. Confirm it's in the roadmap (it must exist as a leaf node)
2. Confirm it's not already `[x]` completed
3. Confirm it's not already `[~]` in progress (unless user wants to re-breakdown)

If the point has an existing items/ doc, ask: "Already has a breakdown. Re-do or view existing?"

### Step 6: Mark Roadmap In Progress

Update the roadmap file: change `- [ ] <point>` to `- [~] <point>`.
If the point already has an items link, preserve it: `- [~] [<point>](items/<name>.md)`.

### Step 7: Delegate to progressive-planner

```
Agent(
  description: "Break down functional point into function items",
  subagent_type: "oh-my-claudecode:progressive-planner",
  model: "opus",
  prompt: "
    Target functional point: <name>
    Spec: <full spec markdown>
    Roadmap: <full roadmap markdown>
    Toolchain: <full toolchain markdown>
    Codebase state: <git log, directory structure, existing items>
    Existing items docs: <list of related items/ files if any>

    Output path: docs/superpowers/items/YYYY-MM-DD-<point-name>.md
    Write the function item document to that path.
  "
)
```

### Step 8: Validate Output

Read the agent's output and check:
- [ ] 5-7 function items
- [ ] Each has a lifecycle tag (交付 | 过渡 | 重构)
- [ ] Each has 1-3 behavioral verification specs (no CLI commands)
- [ ] Dependencies described in plain text (no JSON)
- [ ] Document ≤ 200 lines (excluding mermaid blocks)
- [ ] First item creates a runnable skeleton (e.g., /health)
- [ ] Includes at least one 过渡 item if buildup is needed
- [ ] Includes 重构 item if stepping stones leave temporary code

If validation fails, note specific issues and re-delegate with corrections.

### Step 9: Write and Link

1. Ensure `docs/superpowers/items/` directory exists
2. The agent already wrote the file — verify it's at the expected path
3. Update roadmap: `- [~] <point>` → `- [~] [<point>](items/<date>-<point>.md)`

### Step 10: Gate Summary

Present a compact summary:

```
## 功能项拆解: <functional point>

**拆解思路:** <one sentence from the doc>

**功能项:**
  F-1: <name> (交付) → /health 返回 200
  F-2: <name> (过渡) → POST 创建、GET 查询
  F-3: <name> (交付) → 422 校验错误
  F-4: <name> (交付) → SQLite 持久化
  F-5: <name> (交付) → 完整字段
  F-6: <name> (重构) → 清理内存存储残留

📁 docs/superpowers/items/YYYY-MM-DD-<name>.md

→ "确认？开始 team-lead 执行？" / "哪个功能项要改？"
```

Never dump the full document. The user can read the file.

### Step 11: Handle Gate

- Confirm → done. Suggest: "Ready for team-lead. Run /team-lead with this items doc."
- Change F-N → re-delegate with specific feedback
- Skip → leave DRAFT status

</Steps>

<Tool_Usage>
  - Read: load spec, roadmap, toolchain, existing items docs
  - Bash: explore codebase, git log, directory listing
  - AskUserQuestion: confirm target functional point (show roadmap candidates)
  - Agent: delegate to progressive-planner (model=opus)
  - Write: NOT used — agent writes the items doc
  - Edit: update roadmap checkbox and link
</Tool_Usage>

<Progressive_Principle>
  ONE functional point at a time. Never break down multiple points in one invocation.
  Each function item keeps the system runnable. Progressive disclosure of complexity
  to the human — they see 5-7 items, not 50.
</Progressive_Principle>

<Gate_Behavior>
  Show function item list as gate summary. User confirms before team-lead execution.
</Gate_Behavior>

<Escalation>
  - If agent fails 3 times on same point, present the roadblock and ask user for direct breakdown
  - If user says "just tell me what to build", redirect to team-lead with the items doc
  - If no functional points left to break down, celebrate and suggest /pre-dev for next cycle
</Escalation>
