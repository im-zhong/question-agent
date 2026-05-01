# Logging in Toolchain & Scaffold — Design

**Created:** 2026-05-01
**Last updated:** 2026-05-01
**Status:** DRAFT

## Goal

让 pre-dev toolchain 选型和 scaffold 环境搭建覆盖日志，使项目从第一次迭代就具备集中日志配置，而非事后补丁。

## Problem

当前 toolchain（pre-dev Phase 3）选型时没有日志类别，scaffold 环境搭建时没有日志配置步骤。结果：
- 技术栈文档中日志选型不可见
- 项目只有裸 `logging.getLogger(__name__)` 而无集中配置
- 日志格式、级别、handler 全靠默认行为（WARNING 级别，stderr 输出）

## Design

### 1. Toolchain（pre-dev Phase 3）改动

#### 1.1 Phase 1 技术栈表格

"Logging" 作为必填行，与 web framework、数据库同级。模板示例：

```
| 技术 | 支撑功能 | 选型理由 |
|------|---------|---------|
| stdlib logging | 全模块日志输出 | 零依赖，Python 生态默认选择 |
```

#### 1.2 Brainstorm 提问

现有的 "Do you have tech stack preferences?" 问题保持不变。补充说明：
- 用户选 "No preference" → 按语言默认推荐，不额外提问
- 用户选 "Must use specific tools" → 展开聊日志偏好

默认推荐按语言：
- Python → stdlib logging（零依赖，与已有代码一致）
- TypeScript/Node → winston（社区标准）
- Go → slog（标准库，Go 1.21+）

#### 1.3 Generate 约束

新增约束：**Phase 1 技术栈必须包含 Logging 行。默认推荐按语言生态。**

#### 1.4 Validate 检查

新增检查项：**Phase 1 包含 Logging 技术选择**

#### 1.5 增量更新路径

不受影响。日志选型在 Phase 1 确定后不频繁变化。

### 2. Scaffold 改动

#### 2.1 Phase 2（环境评估）

新增日志配置检查：

```bash
grep -r "logging.basicConfig\|logging.config\|structlog.configure\|loguru" --include="*.py" . 2>/dev/null || echo "NO LOGGING CONFIG"
```

汇总输出新增：

```
已安装:
  ✓ logging config — logging.config.dictConfig in main.py

缺失/不完整:
  ✗ logging config — 无集中日志配置
```

#### 2.2 Phase 4（Tier 判定）

Tier B 定义更新：

| Tier | 包含 |
|------|------|
| A | 语言运行时 + 包管理器 + 依赖管理 |
| B | A + linter + formatter + type checker + test runner + 测试基础设施 + **logging 配置** |
| C | B + pre-commit hooks + CI 骨架 + editorconfig |

Logging 配置从 Tier B 起包含，与 linter/formatter 同级。

#### 2.3 Phase 5（生成计划）

如果 Phase 2 检测到无日志配置且 Tier >= B，plan 新增一项：

```
N. 创建 logging 配置 — 根据工具链选型初始化日志（格式、handler、级别）
```

#### 2.4 Phase 7（执行）

根据工具链中的日志选型生成配置。Python stdlib logging 示例：

- 创建 `<package>/logging_config.py`：包含 `dictConfig` 配置（formatter、handler、默认级别 INFO、结构化格式）
- 在入口文件（如 `main.py`）中调用 `logging_config.setup()` 初始化
- 已有裸 `logging.getLogger(__name__)` 的模块无需改动——它们自然被配置覆盖

#### 2.5 Phase 8（验证）

不变。日志配置是静态文件创建，不额外验证运行时行为。

#### 2.6 Phase 9（报告）

设置列表新增一行：

```
✓ logging config — stdlib logging with dictConfig (INFO, stderr)
```

## Scope

- 只改 pre-dev Phase 3（toolchain）和 scaffold 两个 skill 文件
- 不改代码生成逻辑，不改其他 skill
- 不引入"可观测性"大类——那是未来扩展

## Risks

- **风险:** 不同语言生态的日志默认推荐可能过时 → **备选:** scaffold Phase 3 调研时交叉验证日志库活跃度
