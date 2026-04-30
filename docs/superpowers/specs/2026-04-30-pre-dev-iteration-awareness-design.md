# Pre-Dev 迭代感知 — Design Spec

**Created:** 2026-04-30
**Last updated:** 2026-04-30
**Status:** DRAFT

## Goal

让 pre-dev 从"每次都是第一次"变成"承上启下的迭代工具"：感知当前迭代状态，加载上一轮 summarize 报告作为上下文，智能决定更新策略。

## Target Users

使用 pre-dev → progressive-plan → scaffold → dev-loop → summarize 管线的开发者。

## Key Features

- [ ] Phase 0 重构为"迭代评估"：加载 state.md + summarize + git log，评估 4 信号，推荐模式
- [ ] 三种运行模式：轻量刷新、增量更新、完整重跑
- [ ] 模式决策引擎：4 信号综合判断，用户确认
- [ ] Phase 1-3 自适应行为：每阶段按模式调整（跳过 / 局部更新 / 完整重跑）
- [ ] summarize 报告全局注入：所有阶段共享同一份上下文

## Non-Goals

- 不修改 summarize 技能本身
- 不修改 progressive-plan、scaffold、dev-loop 技能
- 不改变文档输出路径和格式
- 不引入新的文档类型

## Constraints

- 改动限定在 `.claude/skills/pre-dev/SKILL.md` 单个文件内
- 保留现有门控哲学（每个阶段用户确认）
- 向后兼容：首次迭代（无 summarize）行为不变

## Unknowns

- 模式决策规则的实际准确率 — 可能需要多轮迭代调优阈值
- 增量更新的 diff 展示格式用户是否接受

## Design

### Phase 0: Iteration Assessment (重写)

```
Step 0.1 — 加载状态
  读取 docs/superpowers/state.md，解析 iteration、current_phase、文档快照
  不存在 → 标记"首次迭代"，降级为完整重跑

Step 0.2 — 收集迭代上下文（并行）
  加载 spec、roadmap、toolchain（从文档快照）
  搜索 docs/superpowers/summaries/ 找最新报告 → 加载全文
  git log --oneline -10

Step 0.3 — 评估与推荐
  分析 4 信号 → 计算模式 → 给出理由

Step 0.4 — 用户确认
  展示评估摘要 + 推荐模式 + 理由
  用户确认或覆盖
```

### 模式决策逻辑

**信号 1: 文档新旧**
- 对比 spec/roadmap 更新时间 vs git log 最新 commit
- 文档滞后 > 10 commits → 倾向完整重跑
- 文档同步 → 倾向轻量刷新

**信号 2: 变更幅度**
- 从 summarize G 节（量化统计）或 git diff --stat 提取
- +500 行 / 10+ 文件 → 倾向完整重跑
- +100 行以下 / 3 文件以下 → 倾向轻量刷新

**信号 3: 遗留问题严重性**
- 从 summarize D 节提取
- 含架构级问题 → 完整重跑
- 仅小修小补 → 轻量刷新
- 中等（功能未开始、集成未完成）→ 增量更新

**信号 4: 用户显式意图**
- 用户输入含方向变化关键词 → 覆盖其他信号 → 完整重跑
- 用户说"继续"/"下一步" → 不覆盖

**综合规则（优先级从高到低）:**
1. 用户显式意图 → 直接决定
2. 架构级遗留问题 → 完整重跑
3. 文档严重滞后 + 大变更 → 完整重跑
4. 文档同步 + 小变更 + 无严重遗留 → 轻量刷新
5. 其他 → 增量更新（默认）

**缺失 summarize 时:** 降级为完整重跑

### Phase 1-3: 按模式自适应

**Phase 1 (Spec):**
- 轻量刷新：跳过
- 增量更新：加载现有 spec，对比 summarize 更新架构图、追加 Unknowns，展示 diff
- 完整重跑：当前流程 + summarize 全文作为生成上下文

**Phase 2 (Roadmap):**
- 轻量刷新：只勾选已完成项 + 链接已有 items，展示更新后功能树
- 增量更新：勾选完成项 + 吸收 F 节建议追加新功能 + 局部调整结构，展示 diff
- 完整重跑：当前流程 + summarize 全文作为生成上下文

**Phase 3 (Toolchain):**
- 轻量刷新：跳过
- 增量更新：吸收 E 节外部知识 + J 节决策 + K 节经验教训，更新调研记录和风险
- 完整重跑：当前流程 + summarize 全文作为生成上下文

### Phase 4: Final Summary

按模式调整展示内容。轻量刷新展示"下一个功能点"建议；增量/完整重跑标注本轮改动点。

### Phase 5: Update State

不变，所有模式均更新 state.md。

## 展示格式

**Phase 0 评估摘要:**
```
## 迭代评估 — Iteration N

📋 上一轮: summarize/<date>-summary.md
📊 变更: X commits, +Y/-Z 行, W 文件
⚠️ 遗留: N 个

→ 建议: **增量更新**
  理由: ...

选择模式: [轻量刷新 / 增量更新 / 完整重跑]
```
