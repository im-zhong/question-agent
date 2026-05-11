# Logging in Toolchain & Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add logging as a mandatory category in pre-dev toolchain selection and scaffold environment setup.

**Architecture:** Two skill markdown files are modified — pre-dev SKILL.md gets logging in its toolchain phase template/constraints/validation, scaffold SKILL.md gets logging detection, tier inclusion, and setup steps. The existing toolchain document also gets a Logging row.

**Tech Stack:** Markdown skill files only — no runtime code changes.

---

### Task 1: Add logging to pre-dev Phase 3 (Toolchain)

**Files:**
- Modify: `.claude/skills/pre-dev/SKILL.md`

- [ ] **Step 1: Add logging default recommendation to Brainstorm section**

In Phase 3's "完整重跑路径 > Brainstorm + Research" section, after the AskUserQuestion block (line ~548-553), add a note about logging defaults:

```markdown
Also ask about logging if user chose "Must use specific tools":
- "Which logging library?" with options based on language:
  - Python: "stdlib logging (Recommended)", "structlog", "loguru"
  - TypeScript/Node: "winston (Recommended)", "pino"
  - Go: "slog (stdlib, Recommended)"
If user chose "No preference" → use the (Recommended) default for the detected language. No extra question needed.
```

- [ ] **Step 2: Add Logging row to toolchain Output Format template**

In Phase 3's Generate section, the Output Format example table (around line 573) currently has only placeholder rows. Add a Logging row to the example:

Change:
```markdown
| <!-- tech --> | <!-- which roadmap functions this supports --> | <!-- why this choice --> |
```

To:
```markdown
| <!-- tech --> | <!-- which roadmap functions this supports --> | <!-- why this choice --> |
| stdlib logging | 全模块日志输出 | 零依赖，Python 生态默认选择 |
```

- [ ] **Step 3: Add Logging constraint**

In Phase 3's Generate section, Constraints list (around line 593-599), add after "Include at least 1 risk with alternative.":

```markdown
- Phase 1 技术栈必须包含 Logging 行。默认推荐按语言生态（Python→stdlib logging, TypeScript→winston, Go→slog）。
```

- [ ] **Step 4: Add logging to Good example**

In Phase 3's Generate section, Examples > Good (around line 604-606), add a Logging row:

Change:
```markdown
| SQLite | 题目存储、分类查询 | 单机轻量，Phase 1无并发需求 |
```

To:
```markdown
| SQLite | 题目存储、分类查询 | 单机轻量，Phase 1无并发需求 |
| stdlib logging | 全模块日志输出 | 零依赖，Python 默认选择 |
```

- [ ] **Step 5: Add Logging validation check**

In Phase 3's Validate section (around line 630-636), add after the "No massive over-engineering" check:

```markdown
- [ ] Phase 1 包含 Logging 技术选择
```

- [ ] **Step 6: Verify pre-dev SKILL.md changes**

Read the modified file and confirm all 5 changes are present and consistent.

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/pre-dev/SKILL.md
git commit -m "feat(pre-dev): add logging as mandatory toolchain category

Logging is now a required row in Phase 1 tech stack with per-language
defaults (stdlib logging for Python, winston for TS, slog for Go)."
```

---

### Task 2: Add logging to scaffold skill

**Files:**
- Modify: `.claude/skills/scaffold/SKILL.md`

- [ ] **Step 1: Add logging config check to Phase 2**

In Phase 2 (环境评估), after the "已有配置" bash block (around line 113-115), add a new bash block:

```markdown
```bash
# 日志配置
grep -r "logging.basicConfig\|logging.config\|structlog.configure\|loguru" --include="*.py" . 2>/dev/null || echo "NO LOGGING CONFIG"
```
```

In the summary output format (around line 127-136), add logging to both sections:

Under "已安装:" add:
```markdown
  ✓ logging config — <location and method>
```

Under "缺失/不完整:" add:
```markdown
  ✗ logging config — 无集中日志配置
```

- [ ] **Step 2: Update Tier B definition in Phase 4**

In Phase 4 (Tier 判定), Tier definition table (around line 168-170), change Tier B from:

```markdown
| B (core + quality) | A + linter + formatter + type checker + test runner + 测试基础设施 | 大多数项目 |
```

To:

```markdown
| B (core + quality) | A + linter + formatter + type checker + test runner + 测试基础设施 + logging 配置 | 大多数项目 |
```

- [ ] **Step 3: Add logging plan item to Phase 5**

In Phase 5 (生成计划), plan example (around line 209-212), add after the conftest.py item:

```markdown
4. 创建 logging 配置 — 根据工具链选型初始化日志（格式、handler、级别）
```

Renumber subsequent items accordingly.

- [ ] **Step 4: Add logging config execution to Phase 7**

In Phase 7 (执行), after the execution rules (around line 241-244), add a logging-specific rule:

```markdown
- 日志配置根据 toolchain 中 Logging 行的选型生成：
  - stdlib logging → 创建 `<package>/logging_config.py`（dictConfig: INFO 级别, stderr handler, 结构化格式）+ 入口文件调用 `setup()`
  - structlog → 创建 `<package>/logging_config.py`（structlog.configure + stdlib integration）+ 入口文件调用 `setup()`
  - loguru → 创建 `<package>/logging_config.py`（loguru 配置 + 拦截 stdlib logger）+ 入口文件调用 `setup()`
  - 非 Python → 按工具链选型生成对应配置文件
```

- [ ] **Step 5: Add logging to Phase 9 report**

In Phase 9 (报告), settings list (around line 284-286), add:

```markdown
  ✓ <logging-lib> config — <method> (<level>, <output>)
```

- [ ] **Step 6: Verify scaffold SKILL.md changes**

Read the modified file and confirm all 5 changes are present and consistent.

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/scaffold/SKILL.md
git commit -m "feat(scaffold): add logging config to Tier B setup

Logging detection added to Phase 2, logging config included in Tier B,
and setup execution generates logging config based on toolchain selection."
```

---

### Task 3: Update existing toolchain document

**Files:**
- Modify: `.harness/ai-question-agent-toolchain.md`

- [ ] **Step 1: Add Logging row to Phase 1 table**

In the Phase 1 技术栈 table (line 9-17), add after the Jinja2 row:

```markdown
| stdlib logging | 全模块日志输出（知识点识别、题目生成、质量评估链路） | 零依赖，Python 默认选择，已有代码使用 getLogger |
```

- [ ] **Step 2: Verify toolchain document**

Read the modified file and confirm the Logging row is present in Phase 1 table.

- [ ] **Step 3: Commit**

```bash
git add .harness/ai-question-agent-toolchain.md
git commit -m "feat(toolchain): add stdlib logging to Phase 1 tech stack

Logging was missing from the toolchain document despite code already
using getLogger. Adding it makes the tech stack complete."
```
