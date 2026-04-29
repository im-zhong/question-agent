---
name: run
description: Continuous quality-gate runner — checks, auto-fixes, and commits when green
---

# Run — 持续性质量门禁 Runner

核心目标：确保当前进度下的系统**确实可运行**。

## 流程

```
读取上下文 → 质量门禁 → [失败] → 复现测试 → 分析报告 → autopilot 修复 → 循环
                      → [通过] → 功能验证 → conventional commit
```

## Step 1: 读取上下文

必须读全以下文件，形成当前进度快照：

| 文件 | 来源 |
|------|------|
| Spec | `docs/superpowers/specs/*.md` |
| Roadmap (功能树) | `docs/superpowers/plans/*.md` |
| Item (当前功能拆解) | `docs/superpowers/items/*.md` |
| Toolchain | `.harness/*toolchain*.md` |
| Git 状态 | `git status --short && git log --oneline -3` |

**确定当前功能点**：找到 items 文档中第一个状态非 `完成` 的 F-N，打印：
```
当前功能: F-N: <名称> (状态: <待开始/进行中>)
```

## Step 2: 质量门禁

4 道检查，**全部必须通过**：

```bash
# 1. Lint
uv run ruff check .

# 2. Format
uv run ruff format --check .

# 3. Type check
uv run mypy question_agent/

# 4. 单元 + 集成测试（确保服务已启动在 localhost:8000）
uv run pytest -v
```

全部通过 → Step 4。
任一失败 → Step 3。

## Step 3: 失败处理

### 3a. 写复现测试

为每个失败场景写一个最小化回归测试，放到 `tests/` 下。测试必须在修复前失败、修复后通过。

### 3b. 生成分析报告

写到 `.harness/reports/failure-$(date +%Y%m%d-%H%M%S).md`：

```markdown
# Failure Report — <timestamp>

## Failed Check
<ruff|mypy|pytest>

## Error
<exact error output>

## Root Cause
<1-2 sentences>

## Regression Test
<test file path>

## Fix Strategy
<1 sentence>
```

### 3c. 调用 autopilot 修复

将失败报告和回归测试路径传给 `/autopilot`，令其修复。修复后回到 Step 2。

**上限：** 最多循环 5 次。同一错误出现 3 次 → 停止并报告根本性问题。

## Step 4: 功能验证

质量门禁全绿后：

1. 对照当前 item 的验证标准逐条检查
2. 系统行为不满足验证标准 → 标记阻塞，输出原因，停止
3. 全部满足 → 更新 item 文档：`- [x] **状态:** 完成`；同步更新 roadmap 中对应 checkbox

## Step 5: 生成 Commit 并提交

```bash
git diff --stat
git diff
```

生成 conventional commit message：

```
<type>(<scope>): <subject>

<body>

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

Type: `feat` / `fix` / `refactor` / `test` / `chore`
Scope: roadmap 中的功能域名（如 `教材知识抽取`）

执行提交：
```bash
git add <改动的具体文件>
git commit -m "$(cat <<'EOF'
<commit message>
EOF
)"
```

打印：`Committed: <hash> — <subject>`

## Step 6: 下一步提示

扫描 roadmap 下一个 `[ ]` 叶子节点，提示：
```
下一个功能点: <名称>
→ /progressive-plan 拆解 或 /run 继续
```

## 关键约束

- **不跳过检查**：任何一道门禁失败都必须进入 Step 3
- **不改需求**：修复只针对代码，不修改 spec/roadmap/item 中的功能定义
- **失败上限**：Step 2→3→2 循环最多 5 次；同一错误 3 次即停止
- **必须先读上下文再跑门禁**：不能跳过 Step 1
