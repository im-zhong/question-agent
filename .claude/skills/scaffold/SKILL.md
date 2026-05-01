---
name: scaffold
description: 文档驱动的环境搭建 — 基于 pre-dev 文档和仓库现状构建可开发可测试的环境，不确定时与用户讨论
argument-hint: "[tier]"
triggers:
  - "scaffold"
  - "setup"
  - "环境搭建"
  - "准备环境"
  - "搭建开发环境"
  - "setup dev"
  - "setup environment"
level: 4
---

<Purpose>
  承上启下。读取 pre-dev 产出的 spec/roadmap/toolchain/summarize 文档和仓库现有配置，
  以 toolchain 为期望基准评估当前环境，搭建缺失部分，最终验证开发服务器和测试框架均可运行。
  
  是 progressive-plan 之后、dev-loop 之前的桥梁 — 确保开发开始前环境就绪。
</Purpose>

<Use_When>
  - progressive-plan 完成后，dev-loop 开始前
  - 新成员加入项目需要初始化本地环境
  - toolchain 更新后需要同步环境
  - 用户说 "scaffold"、"setup"、"搭建环境"、"准备开发环境"
</Use_When>

<Do_Not_Use_When>
  - 还没运行 pre-dev — 先完成 pre-dev 生成 toolchain
  - 做代码质量检查 — 那是 run skill 的职责
  - 项目初始化 — 不替代 uv init/cargo init 等
</Do_Not_Use_When>

<Execution_Policy>
  - 9 个顺序 Phase，每个 Phase 完成后再进入下一个
  - Phase 6 是唯一与用户交互的节点 — 只在不确定时问，不做向导式逐条询问
  - Phase 5 生成的 plan 必须获得用户批准后才能进入 Phase 7 执行
  - 所有修改文件系统的操作（安装、写配置）必须有 plan 和批准
  - 可重入：Phase 2 评估保证每次运行只做增量
</Execution_Policy>

<Hard_Rules>

从原 scaffold subagent 继承的核心约束，整个 skill 执行期间严格遵守：

1. **Never execute before approval** — 任何修改文件系统的操作必须先展示 plan 并获得用户批准
2. **Always research — don't trust training data** — 工具生态变化快，Phase 3 做 web search 确认当前推荐
3. **Graduate the tier based on context, not defaults** — 基于迭代阶段 + 文档内容 + 仓库现状决定 tier
4. **Every plan item answers WHAT and WHY** — 如 "添加 ruff — lint + format 一个工具替代 flake8+isort+black"
5. **Context before questions** — 先扫描仓库（已有配置、lockfile、CI 文件），再问针对性问题

</Hard_Rules>

<Steps>

### Phase 1: 加载上下文

**Step 1.1 — 加载 state.md**

读取 `docs/superpowers/state.md`：
- 存在 → 解析 frontmatter（iteration、current_phase）和文档快照表，提取 spec/roadmap/toolchain/summarize 路径
- 不存在 → 标记 iteration=1，从 git log + 文档目录自动推断

**Step 1.2 — 并行加载所有文档**

| 来源 | 内容 | 用途 |
|------|------|------|
| toolchain | 期望的工具列表、版本、All Checks 命令 | 环境期望基准 |
| spec | 项目类型、约束 | 判断项目类型和需求 |
| roadmap | 当前功能范围 | 判断需要的测试基础设施级别 |
| summarize | 经验教训（K 节）、外部知识（E 节） | 避免重复踩坑 |
| pyproject.toml | 已声明依赖、已有工具配置 | 与 toolchain 对比验证 |
| 已有配置文件 | .editorconfig, CI 文件, Makefile, .gitignore 等 | 避免重复/冲突配置 |

如果 toolchain 文件不存在 → 报错退出：
```
未找到 toolchain 文件。请先运行 /pre-dev 生成技术栈和工具链文档。
```

### Phase 2: 环境评估

逐项检查当前状态（并行执行）：

```bash
# 包管理器
uv --version 2>/dev/null || echo "NOT INSTALLED"

# 依赖同步
uv lock --check 2>&1 || echo "OUTDATED"

# linter
ruff --version 2>/dev/null || echo "NOT INSTALLED"

# type checker
mypy --version 2>/dev/null || echo "NOT INSTALLED"

# test runner
pytest --version 2>/dev/null || echo "NOT INSTALLED"
```

```bash
# 测试基础设施
ls tests/ 2>/dev/null && echo "EXISTS" || echo "MISSING"
ls tests/conftest.py 2>/dev/null && echo "EXISTS" || echo "MISSING"
# Integration test infrastructure
ls tests/integration/ 2>/dev/null && echo "EXISTS" || echo "MISSING"
ls tests/integration/conftest.py 2>/dev/null && echo "EXISTS" || echo "MISSING"
```

```bash
# 已有配置
cat pyproject.toml 2>/dev/null | head -80
ls .editorconfig 2>/dev/null || echo "NO .editorconfig"
ls .pre-commit-config.yaml 2>/dev/null || echo "NO pre-commit"
ls .github/workflows/*.yml 2>/dev/null || echo "NO CI workflows"
```

```bash
# 日志配置
grep -r "logging.basicConfig\|logging.config\|structlog.configure\|loguru" --include="*.py" . 2>/dev/null || echo "NO LOGGING CONFIG"
```

汇总输出格式：

```
## 环境评估 — Iteration <N>

已安装:
  ✓ uv 0.10.x
  ✓ ruff 0.15.x
  ✓ pytest 9.x
  ✓ mypy 1.20.x
  ✓ logging config — <location and method>

缺失/不完整:
  ✗ pre-commit hooks — 未安装
  ✗ conftest.py — 不存在
  ✗ CI workflows — 不存在
  ✗ logging config — 无集中日志配置

已有配置:
  ○ pyproject.toml — ruff + pytest 配置完整
  ○ .editorconfig — 存在
```

### Phase 3: 调研

对 toolchain 中每类工具和当前缺失的工具类别，web search 确认当前最佳实践：

搜索模式：`"best {category} for {language} {current year}"` 或 `"{tool} vs {alternative} {current year}"`

交叉验证问题：
- 工具是否活跃维护？（最近 release 在 6 个月内）
- 是否是社区标准？（GitHub stars、下载量趋势）
- toolchain 推荐的版本是否仍然合适？

无网络时：跳过 web search，回退到训练知识，在 plan 中标注 "⚠️ 基于训练知识，可能不是最新推荐"。

Gate：每个需要决策的工具类别至少 1-2 个候选方案。

### Phase 4: Tier 判定

基于以下信号推荐 tier：

| 信号 | 来源 | Tier A | Tier B | Tier C |
|------|------|--------|--------|--------|
| 迭代次数 | state.md frontmatter | 1-2 | 3-5 | 6+ |
| 项目类型 | spec | 脚本/实验 | library/service | 团队/开源 |
| 已有工具 | Phase 2 评估 | 无或极少 | 基础工具已装 | 大部分已装 |
| 功能范围 | roadmap 功能域数量 | 1-2 域 | 3-4 域 | 5+ 域 |

Tier 定义：

| Tier | 包含 | 适用场景 |
|------|------|---------|
| A (core runtime) | 语言运行时 + 包管理器 + 依赖管理 | 早期迭代、一次性脚本、实验项目 |
| B (core + quality) | A + linter + formatter + type checker + test runner + 测试基础设施 + logging 配置 | 大多数项目 |
| C (full kit) | B + pre-commit hooks + CI 骨架 + editorconfig | 后期迭代、团队项目、长期维护 |

综合规则：
1. 迭代次数为主要信号（权重最高）
2. 已有工具不会降级 — 如果评估发现 B 级工具已装好，不降级到 A
3. roadmap 功能域 >= 3 且有团队协作迹象 → 至少 B
4. 最终由用户确认，允许升降级

展示并让用户确认：

```
## Tier 推荐 — Iteration <N>

信号:
  迭代: <N> | 项目类型: <type> | 功能域: <M> 个

推荐: **Tier <X>** (<label>)
理由: <2-3 句话解释>

包含:
  - <item 1>
  - <item 2>
  - ...
```

使用 AskUserQuestion 确认：
- "Tier B (Recommended)"
- "Tier A — 降级，只保留核心运行时"
- "Tier C — 升级，加 pre-commit hooks 和 CI 骨架"

### Phase 5: 生成计划

对比 "Phase 2 现状" vs "Phase 4 确认的 Tier 期望"，生成执行计划。

每项格式：`序号. 操作 — WHAT + WHY`

示例：
```
1. uv sync — 同步依赖，确保与 pyproject.toml 和 lockfile 一致
2. 更新 pyproject.toml — 补充 ruff format 配置和 pytest 选项
3. 创建 tests/conftest.py — 共享 pytest fixtures（async client, test data）
4. 创建 tests/integration/conftest.py — 集成测试 fixtures（live server client, base_url, reachability check）
5. 创建 tests/integration/fixtures/ — 集成测试 fixture 文件目录
6. 创建 logging 配置 — 根据工具链选型初始化日志（格式、handler、级别）
7. 编写 .editorconfig — 统一缩进和字符集设置
```

如果无需操作：
```
环境已就绪。Tier B 所需工具全部安装并配置完成。
→ 跳过 Phase 7，直接进入 Phase 8 验证。
```

Gate：使用 AskUserQuestion 确认："执行此 plan？" — 用户可增删改后再执行。

### Phase 6: 讨论不确定项

只在以下场景使用 AskUserQuestion：

- toolchain 要求版本与已安装版本冲突 → "保留当前 x.x.x 还是安装 toolchain 要求的 y.y.y？"
- 调研发现 toolchain 推荐的工具已不推荐/停止维护 → "建议用 X 替代 Y，原因..."
- 发现 toolchain 未覆盖的工具类别 → "需要 X 吗？"
- 非标准环境（nix shell、devcontainer、docker-only）→ "检测到 X 环境，保留还是改用标准工具？"
- 多个可选项难以自动判断 → 列出 2-3 选项让用户选
- Monorepo 多技术栈 → "要 scaffold 哪个部分？"
- 冲突的已有配置 → "发现 `.flake8`，ruff 已替代它。是否移除旧配置？"

不做逐类别向导式询问。只问真正需要用户判断的问题。

### Phase 7: 执行

按 Phase 5 批准的计划顺序执行。

执行规则：
- 先安装包管理器（如果需要），再安装工具，最后写配置文件
- 每步安装后快速验证工具可用（如 `ruff --version`）
- 失败项标记 `✗` 并跳过依赖项，继续独立项
- 不使用 `sudo` — 权限不足时记录精确的手动修复命令
- 日志配置根据 toolchain 中 Logging 行的选型生成：stdlib logging → 创建 `<package>/logging_config.py`（dictConfig: INFO 级别, stderr handler, 结构化格式）+ 入口文件调用 `setup()`；structlog → 创建 `<package>/logging_config.py`（structlog.configure + stdlib integration）+ 入口文件调用 `setup()`；loguru → 创建 `<package>/logging_config.py`（loguru 配置 + 拦截 stdlib logger）+ 入口文件调用 `setup()`；非 Python → 按工具链选型生成对应配置文件

进度报告格式：

```
EXECUTING:
  ✓ Step 1: uv sync — 依赖已同步
  ✓ Step 2: ruff config — pyproject.toml 已更新
  ✗ Step 3: pre-commit install — 失败 (git repo 未初始化)
  ○ Step 4: conftest.py — 已存在，跳过
```

### Phase 8: 验证

两件事都必须验证：

**开发环境：**
```bash
timeout 5 uv run uvicorn question_agent.main:app --port 8000 2>&1 || true
```
- 检查输出：确认无 import 错误、FastAPI app 成功加载
- 如果端口被占用，用 `--port 0` 或换端口重试

**测试环境：**
```bash
uv run pytest --collect-only 2>&1
uv run pytest tests/integration/ --co -q 2>&1
```
- 确认 pytest 可以收集测试（不要求通过 — 那是 run 的职责）
- 如果收集数为 0，提示可能需要添加测试
- Integration test collection confirms the infrastructure is set up (tests may skip if server not running)

任一项失败 → 标记原因，给出诊断建议，不阻塞报告。

### Phase 9: 报告

```
## Scaffold 完成 — Iteration <N>

Tier: <X> (<label>)

设置:
  ✓ <tool-1> <version> — <note>
  ✓ <tool-2> <version> — <note>
  ✓ <logging-lib> config — <method> (<level>, <output>)
  ...

跳过:
  ○ <item> — <reason>

验证:
  ✓ 开发服务器可启动 (localhost:8000)
  ✓ pytest 可运行 (<N> tests collected)

下一步: /dev-loop
```

如果有失败项：
```
⚠️ 手动修复:
  1. <manual fix command> — <reason>
```

</Steps>

<Tool_Usage>
  - Read: 加载 state.md、spec、roadmap、toolchain、summarize、pyproject.toml、已有配置文件
  - Bash: 版本检查（uv/ruff/mypy/pytest --version）、依赖状态（uv lock --check）、验证命令
  - WebSearch: Phase 3 调研工具现状
  - AskUserQuestion: Phase 4 Tier 确认、Phase 5 Plan 批准、Phase 6 不确定项讨论
  - Write: 创建/更新配置文件（pyproject.toml、conftest.py、.editorconfig 等）
  - Edit: 局部修改已有配置文件
</Tool_Usage>

<Escalation>
  - toolchain 文件不存在 → 报错，提示先运行 /pre-dev
  - 环境已就绪（无任何操作）→ 快速跳过 Phase 7，直接进入 Phase 8 验证
  - 工具安装连续失败 3 个以上 → 停止，怀疑网络或权限问题，提示用户检查
  - 验证失败 → 标记失败项，给出诊断建议，不阻塞
  - 无网络 → 跳过 Phase 3 web search，回退到训练知识，在 plan 中标注
  - 权限不足 → 记录精确的手动修复命令，不使用 sudo
</Escalation>

<Final_Checklist>
  - [ ] state.md 加载成功，文档路径已提取
  - [ ] 全部 pre-dev 文档（spec/roadmap/toolchain/summarize）已加载
  - [ ] 环境评估完成（Phase 2）
  - [ ] 调研完成（Phase 3，或无网络时已标注跳过）
  - [ ] Tier 已确定并经用户确认（Phase 4）
  - [ ] Plan 已生成并经用户批准（Phase 5）
  - [ ] 不确定项已讨论（Phase 6，或无需讨论）
  - [ ] Plan 执行完成，失败项已标记（Phase 7）
  - [ ] 开发服务器验证通过（Phase 8）
  - [ ] 测试框架验证通过（Phase 8）
  - [ ] 报告已展示（Phase 9）
</Final_Checklist>
