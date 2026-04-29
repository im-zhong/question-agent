---
name: run
description: Continuous quality-gate runner — checks, edge-case tests, auto-fixes, and commits when green
---

# Run — 持续性质量门禁 Runner

核心目标：确保当前进度下的系统**确实可运行**，且**边缘情况已被主动覆盖**。

## 流程

```
读取上下文 → 质量门禁 → 边缘测试 → [失败] → 复现测试 → 分析报告 → autopilot 修复 → 循环
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

全部通过 → Step 3。
任一失败 → Step 5（失败处理）。

## Step 3: 边缘情况主动测试

质量门禁通过后，**Runner 必须主动分析当前已实现功能，自行编写边缘情况测试**，而不是仅依赖文档中列出的验证项。

### 3a. 分析攻击面

对当前已实现的所有端点/模块，按以下维度逐一审视：

| 维度 | 思考方向 |
|------|---------|
| 输入边界 | 空值、超长字符串、特殊字符（Unicode/emoji/零宽字符）、二进制数据伪装成文本 |
| MIME/类型欺骗 | Content-Type 与文件内容不一致、无扩展名、伪造扩展名 |
| 并发 | 同一端点并发请求、上传同名文件 |
| 编码 | 非 UTF-8 编码（GBK/Shift-JIS/Latin-1）、BOM 头、混合编码 |
| 大小 | 0 字节、1 字节、刚好等于上限、上限+1 字节 |
| HTTP 方法 | 用 GET/PUT/DELETE 调 POST 端点、OPTIONS/HEAD |
| Header | 缺失 Content-Type、畸形 multipart、超大 header |
| 资源耗尽 | 慢速上传（slowloris 式）、嵌套 ZIP bomb 式压缩文件（如适用） |

### 3b. 编写边缘测试

针对发现的每个潜在漏洞/边界，写一个最小化测试放入 `tests/`，命名 `test_edge_<描述>.py`。

测试必须：
- 能独立运行：`uv run pytest tests/test_edge_<描述>.py -v`
- 有明确的预期行为（200/422/413/...），不假设实现细节
- 优先关注**可能导致 500 或服务崩溃**的场景

### 3c. 跑新测试

```bash
uv run pytest tests/test_edge_*.py -v
```

- 全部通过 → Step 6（功能验证）
- 任一失败 → Step 4（生成边缘失败报告）→ Step 5（失败处理）

## Step 4: 边缘失败报告

如果边缘测试发现**新问题**（非已有测试覆盖的失败），生成报告：

写到 `.harness/reports/edge-failure-$(date +%Y%m%d-%H%M%S).md`：

```markdown
# Edge Case Failure Report — <timestamp>

## Edge Test
<test file path>

## Test Scenario
<what edge case was being tested>

## Failure
<exact error output / stack trace>

## Severity
<critical: 导致 500/崩溃 | high: 行为不符合预期 | low: 边界模糊>

## Root Cause
<1-2 sentences>

## Fix Strategy
<1 sentence>
```

然后进入 Step 5。

## Step 5: 失败处理

### 5a. 写复现测试

为每个失败场景写一个最小化回归测试，放到 `tests/` 下。测试必须在修复前失败、修复后通过。

（Step 3/4 中新发现的边缘问题已经生成了测试，若为已有测试失败，则需额外写回归测试。）

### 5b. 生成分析报告

写到 `.harness/reports/failure-$(date +%Y%m%d-%H%M%S).md`：

```markdown
# Failure Report — <timestamp>

## Failed Check
<ruff|mypy|pytest|edge-case>

## Error
<exact error output>

## Root Cause
<1-2 sentences>

## Regression Test
<test file path>

## Fix Strategy
<1 sentence>
```

### 5c. 调用 autopilot 修复

将失败报告和回归测试路径传给 `/autopilot`，令其修复。修复后回到 Step 2。

**上限：** 最多循环 5 次。同一错误出现 3 次 → 停止并报告根本性问题。

## Step 6: 功能验证

质量门禁 + 边缘测试全绿后：

1. 对照当前 item 的验证标准逐条检查
2. 系统行为不满足验证标准 → 标记阻塞，输出原因，停止
3. 全部满足 → 更新 item 文档：`- [x] **状态:** 完成`；同步更新 roadmap 中对应 checkbox

## Step 7: 生成 Commit 并提交

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

## Step 8: 下一步提示

扫描 roadmap 下一个 `[ ]` 叶子节点，提示：
```
下一个功能点: <名称>
→ /progressive-plan 拆解 或 /run 继续
```

## 关键约束

- **不跳过检查**：任何一道门禁失败都必须进入 Step 5
- **必须主动写边缘测试**：Step 3 不可跳过，Runner 必须产出至少 1 个边缘测试文件
- **不改需求**：修复只针对代码，不修改 spec/roadmap/item 中的功能定义
- **失败上限**：Step 2→5→2 循环最多 5 次；同一错误 3 次即停止
- **必须先读上下文再跑门禁**：不能跳过 Step 1
