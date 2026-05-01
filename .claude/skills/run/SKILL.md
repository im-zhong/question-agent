---
name: run
description: Continuous quality-gate runner — checks, edge-case tests, walkthrough, auto-fixes, and commits when green
---

# Run — 持续性质量门禁 Runner

核心目标：确保当前进度下的系统**确实可运行**，且**边缘情况已被主动覆盖**。

## 流程

```
读取上下文 → 质量门禁 → 边缘测试 → 启动系统 + 功能走查 → 功能验证 → conventional commit
                 ↓ 失败                ↓ 失败
                 └→ 失败处理 ──────────┘
                       ↓ 修复后
                    质量门禁 → ... → 功能走查
```

## Step 1: 读取上下文

必须读全以下文件，形成当前进度快照：

| 文件 | 来源 |
|------|------|
| Spec | `docs/superpowers/specs/*.md` |
| Roadmap (功能树) | `docs/superpowers/plans/*.md` |
| Item (当前功能拆解) | `docs/superpowers/items/*.md` |
| Toolchain | `.harness/*toolchain*.md`（含 `## Walkthrough` 段落） |
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

- 全部通过 → Step 6（启动系统 + 功能走查）
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
<ruff|mypy|pytest|edge-case|walkthrough>

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

**走查失败的特殊路径：** 走查失败修复后，先过 Step 2（质量门禁）→ Step 3 → Step 6（重新走查），确保修复没有引入新的静态问题。

## Step 6: 启动系统 + 功能走查

**这是最后一道门禁。** 走查不通过不 commit。

### 6a. 启动系统

从 toolchain 文档 `## Walkthrough` 段落读取启动配置：

| 配置项 | 用途 |
|--------|------|
| Start Command | 后台启动 dev server |
| Health Check | 轮询确认 server 就绪 |
| Shutdown Signal | 关停 server |
| Port | 端口检测 |

**启动流程**：

1. 检查端口是否已被占用（向 Health Check 端点发请求）
   - 已占用 → 询问用户是否复用已有实例，还是关停后重启
   - 空闲 → 继续
2. 后台启动 dev server（`Start Command`）
3. 轮询 Health Check 端点，每 2 秒一次，最长等待 30 秒
   - 就绪 → 继续
   - 超时 → 报告启动失败，进入 Step 5

### 6b. 分析端点 + 补写走查测试

与 Step 3（主动写边缘测试）同样的模式——缺测试就写，不跳过：

1. 分析代码中已注册的所有端点/功能入口
2. 对比 `tests/integration/` 中已有的走查测试
3. 缺失走查测试的端点 → **必须主动编写**对应的走查测试
4. 编写后运行确认新测试可执行

### 6c. 运行功能走查

```bash
uv run pytest tests/integration/ -v
```

- 全部通过 → Step 6d（关停 server），然后 Step 7（功能验证）
- 任一失败 → Step 6d（关停 server），然后 Step 5（失败处理）

### 6d. 关停系统

走查完成后（无论成功失败），向 server 进程发 SIGTERM。如果进程 5 秒内未退出，发 SIGKILL 强杀。

## Step 7: 功能验证

质量门禁 + 边缘测试 + 功能走查全绿后：

1. 对照当前 item 的验证标准逐条检查
2. 系统行为不满足验证标准 → 标记阻塞，输出原因，停止
3. 全部满足 → 更新 item 文档：`- [x] **状态:** 完成`；同步更新 roadmap 中对应 checkbox

## Step 8: 生成 Commit 并提交

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

## Step 9: 下一步提示

扫描 roadmap 下一个 `[ ]` 叶子节点，提示：
```
下一个功能点: <名称>
→ /progressive-plan 拆解 或 /run 继续
```

## 关键约束

- **不跳过检查**：任何一道门禁失败都必须进入 Step 5
- **必须主动写边缘测试**：Step 3 不可跳过，Runner 必须产出至少 1 个边缘测试文件
- **必须主动写走查测试**：Step 6b 不可跳过，缺失走查测试必须补写
- **功能走查是最终门禁**：Step 6 不通过不 commit
- **修复后先过质量门禁**：走查失败修复后必须先过 Step 2，再重新走查
- **server 必须关停**：Step 6d 无论成功失败都关停，不留残留进程
- **不改需求**：修复只针对代码，不修改 spec/roadmap/item 中的功能定义
- **失败上限**：Step 2→5→2 循环最多 5 次；同一错误 3 次即停止
- **必须先读上下文再跑门禁**：不能跳过 Step 1
