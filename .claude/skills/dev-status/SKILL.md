---
name: dev-status
description: Read-only project state viewer — shows current iteration, cycle history, document index, and quick stats
argument-hint: "[ 'iter <N>' ]"
triggers:
  - "status"
  - "项目状态"
  - "当前进度"
  - "迭代状态"
  - "where are we"
level: 3
---

<Purpose>
  快速查看当前迭代状态和循环历史。纯读 — 不写文件、不做推理。
  状态由 pre-dev / progressive-plan / summarize 在收尾时自动维护。
</Purpose>

<Use_When>
  - 想知道当前处于第几次迭代、哪个 Phase
  - 想查看之前迭代的产出和决策
  - 下一轮 pre-dev 前需要快速回顾
  - 用户说 "status"、"项目状态"、"当前进度"
</Use_When>

<Do_Not_Use_When>
  - 需要手动修改状态 — 状态修改是其他 skill 的副作用
  - 需要详细分析 — 这是查看器，不是分析器
</Do_Not_Use_When>

<Execution_Policy>
  - 只读。不写文件，不跑 git，不做 web search
  - state.md 缺失时提示用户先运行 pre-dev
</Execution_Policy>

<Steps>

### Step 1: Route

| 输入 | 行为 |
|------|------|
| `/status` | 打印 state.md 内容 |
| `/status iter <N>` | 打印 `docs/superpowers/iterations/<NN>-<date>.md` |
| `/status iter <N>` 但文件不存在 | 列出所有可用的迭代文件 |

### Step 2: Print state.md

直接 Read `docs/superpowers/state.md` 并展示给用户。

如果文件不存在：
```
无状态记录。docs/superpowers/state.md 不存在。

运行 /pre-dev "<描述>" 开始第一次迭代，或 /summarize 会自动重建状态。
```

### Step 3: Print Iteration Detail (if requested)

1. 解析 `<N>` — 支持 `1`、`01` 两种格式
2. Glob `docs/superpowers/iterations/<NN>-*.md` 找匹配文件
3. Read 并展示

如果用户输入 `/status iter 3` 但只有 1、2 两个迭代文件：
```
可用迭代: 1, 2。使用 /status iter <N> 查看详情。
```

</Steps>

<Tool_Usage>
  - Read: 读取 state.md 和 iterations/NN-date.md
  - Glob: 查找迭代文件列表
</Tool_Usage>

<Escalation>
  - state.md 缺失 → 提示用户运行 pre-dev 或 summarize 重建
  - 迭代文件不存在 → 列出可用编号
</Escalation>

<State_File_Spec>
  (Reference for other skills that WRITE state — status skill only reads.)

  ### state.md format

  ```markdown
  ---
  iteration: <N>
  current_phase: "<phase name>"
  status: <pre-dev | progressive-plan | dev | summarize>
  updated: <YYYY-MM-DD>
  ---

  # 项目状态

  **当前迭代：** <N>
  **当前阶段：** <phase> — <status>
  **下一个待办：** <one-line hint>

  ## 迭代索引

  | # | 日期 | 说明 | 详情 |
  |---|------|------|------|
  | 1 | 04-25 ~ 04-28 | 初始搭建 | [→](iterations/01-2026-04-25.md) |

  ## 文档快照

  | 类型 | 路径 | 状态 |
  |------|------|------|
  | spec | specs/<date>-<name>.md | confirmed |
  | roadmap | plans/<date>-<name>-roadmap.md | confirmed |
  | toolchain | .harness/<name>-toolchain.md | draft |
  | summary | summaries/<date>-summary.md | final |
  ```

  ### iterations/NN-date.md format

  ```markdown
  ---
  iteration: <N>
  date_start: <YYYY-MM-DD>
  date_end: <YYYY-MM-DD>
  stages: [pre-dev, progressive-plan, dev, summarize]
  ---

  # 迭代 <N> — <date_start> ~ <date_end>

  ## 流程

  | 阶段 | 日期 | 产出 | 状态 |
  |------|------|------|------|
  | pre-dev | <date> | spec, roadmap, toolchain | ✅ |
  | progressive-plan | <date> | Phase 1-3 roadmap | ✅ |
  | dev | <date range> | 核心功能 | ✅ |
  | summarize | <date> | [summary](summaries/<date>-summary.md) | ✅ |

  ## 产出文件
  - [spec](specs/<date>-<name>.md)
  - [roadmap](plans/<date>-<name>.md)
  - ...

  ## 统计
  - Commits: <N>
  - 新增代码: +<N> 行
  - 测试: <N> 新增，<N>/<N> 通过

  ## 关键决策
  - <decision summary>（详情见 summary J section）

  ## 遗留
  - <issue summary>（详情见 summary D section）
  ```
</State_File_Spec>
