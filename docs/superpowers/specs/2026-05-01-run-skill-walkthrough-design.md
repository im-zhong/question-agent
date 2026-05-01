# Run Skill — 功能走查设计

**Date:** 2026-05-01
**Status:** DRAFT

## 问题

当前 run skill 有质量门禁（lint/type/test）和边缘测试，但没有验证**系统是否能实际运行**。这是最根本的检查——系统不能启动或端点不能响应，其他检查都没有意义。

## 目标

在 run skill 流程中增加「启动系统 + 功能走查」步骤，作为最后一道门禁：走查成功才能 commit，走查失败则修复后必须先过质量门禁再重跑走查。

## 设计

### 新流程

```
读取上下文 → 质量门禁 → 边缘测试 → 启动系统 + 功能走查 → 功能验证 → commit → 下一步提示
                                          ↓ 失败
                                    写回归测试 → autopilot 修复 → 质量门禁 → 重新走查
```

### 步骤变更

| Step | 名称 | 变更 |
|------|------|------|
| 1 | 读取上下文 | 新增读取 toolchain 文档的 `## Walkthrough` 段落 |
| 2 | 质量门禁 | 无变更 |
| 3 | 边缘情况主动测试 | 无变更 |
| 4 | 边缘失败报告 | 无变更 |
| 5 | 失败处理 | **扩展**：走查失败也走此步骤；修复后先过质量门禁再重走查 |
| 6 | **启动系统 + 功能走查** | **新增**（见下文详细设计） |
| 7 | 功能验证 | 无变更 |
| 8 | 生成 commit | 无变更 |
| 9 | 下一步提示 | 无变更 |

### Step 6 详细设计：启动系统 + 功能走查

#### 6a. 启动系统

从 toolchain 文档 `## Walkthrough` 段落读取启动配置：

```markdown
## Walkthrough

| 配置项 | 值 |
|--------|-----|
| Start Command | `uv run question-agent` |
| Health Check | `GET /docs` → 200 |
| Shutdown Signal | SIGTERM |
| Port | 8000 |
```

**启动流程**：

1. 检查端口是否已被占用（向 Health Check 端点发请求）
   - 已占用 → 询问用户是否复用已有实例，还是关停后重启
   - 空闲 → 继续
2. 后台启动 dev server（`Start Command`）
3. 轮询 Health Check 端点，每 2 秒一次，最长等待 30 秒
   - 就绪 → 继续
   - 超时 → 报告启动失败，进入 Step 5

#### 6b. 分析端点 + 补写走查测试

与 Step 3（主动写边缘测试）同样的模式——缺测试就写，不跳过：

1. 分析代码中已注册的所有端点/功能入口
2. 对比 `tests/integration/` 中已有的走查测试
3. 缺失走查测试的端点 → 主动编写对应的走查测试
4. 编写后运行 `uv run pytest tests/integration/ -v` 确认新测试可执行

#### 6c. 运行功能走查

```bash
uv run pytest tests/integration/ -v
```

- 全部通过 → 关停 server，进入 Step 7（功能验证）
- 任一失败 → 关停 server，进入 Step 5（失败处理），修复后走 Step 2（质量门禁）→ ... → Step 6（重跑走查）

#### 6d. 关停系统

走查完成后（无论成功失败），向 server 进程发 SIGTERM。如果进程 5 秒内未退出，发 SIGKILL 强杀。

### 失败循环

原 Step 5→2 循环扩展为两条路径：

- **质量门禁/边缘测试失败** → Step 5 修复 → Step 2（重跑质量门禁）→ Step 3 → Step 6
- **功能走查失败** → Step 5 修复 → Step 2（先过质量门禁）→ Step 3 → Step 6（重跑走查）

关键约束：走查失败修复后必须先过质量门禁，才能重新走查。这确保修复没有引入新的静态问题。

### 走查测试组织

```
tests/
  integration/
    test_walkthrough.py    # 单端点走查：每个端点一个测试函数
    test_flows.py          # 业务流程走查：跨端点链路
    fixtures/              # fixture 文件（PDF 样本等）
    conftest.py            # base_url fixture、server 启停 helper
```

**走查测试职责**：
- 调用每个已实现的 API 端点，验证返回合理状态码和响应结构
- 验证端到端业务链路（如上传教材 → 章节识别 → 知识点抽取）
- 硬编码基础请求数据 + fixture 目录存复杂样本文件

**新增端点时的约定**：progressive-plan 拆解功能点时，实现步骤包含编写走查测试。run skill 执行时补漏。

### Toolchain 文档变更

新增 `## Walkthrough` 段落，定义启动命令、健康检查、关停信号、端口。

### 关联 Skill 变更

| Skill | 变更 |
|-------|------|
| progressive-plan | 拆解功能点时，实现步骤包含编写/更新 `tests/integration/` 走查测试 |
| scaffold | 创建 `tests/integration/` 目录结构和 `conftest.py` 基础配置 |
| dev-loop | 无需修改，Step 4 调用 `/run` 自然包含走查 |
| CLAUDE.md | Commands 段落补充集成测试运行方式 |

### 关键约束

- **功能走查不可跳过**：Step 6 是最后一道门禁，走查不通过不 commit
- **缺走查测试必须补写**：和边缘测试一样，缺测试就写，不跳过
- **修复后先过质量门禁**：走查失败修复后必须先过 Step 2，再重新走查
- **server 必须关停**：走查完成后无论成功失败都关停 server，不留残留进程
- **失败上限不变**：Step 5 循环最多 5 次，同一错误 3 次停止
