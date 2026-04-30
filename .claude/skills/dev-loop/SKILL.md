---
name: dev-loop
description: Autonomous develop-and-verify loop — autopilot implements, run verifies, repeats until CURRENT item complete, then stops
---

# Dev-Loop — 自主开发验证循环

```
Step1(上下文) → Step2(找F-N) → Step3(/autopilot) → Step4(/run 强制) → 循环
```

**核心规则：Step 3 和 Step 4 各自独立执行，Step 4 不可跳过。**

## Step 1: 读取上下文

找到 `docs/superpowers/items/*.md` 中状态为 `进行中` 的文档。
打印已完成/待开始的 F-N 列表。

## Step 2: 找下一个功能点

扫描 item 文档，找第一个 `- [ ] **状态:** 待开始` 的 F-N。

- 找不到 → Step 5（收尾）
- 找到 → 打印 `当前: F-N: <名称>`，**进入 Step 3**

## Step 3: /autopilot 实现

**只做一件事**：委派 `/autopilot` 实现当前 F-N。

调用方式：
```
Skill("autopilot", "<F-N>: <目标>\n验证标准：...\n依赖：...")
```

等待 autopilot 完成全部 5 个 Phase（Expansion/Planning/Execution/QA/Validation）。

**autopilot 完成后，禁止继续写代码。必须进入 Step 4。**

## Step 4: /run 验证（强制，不可跳过）

**这是整个循环的关键节点。不管 autopilot 看起来多么完美，都必须执行此步骤。**

调用 `/run` skill 完成：
- 质量门禁（ruff + mypy + pytest）
- 边缘情况主动测试（Step 3 — 自己写边缘测试）
- 失败修复循环
- 功能验证 + conventional commit

**`/run` 成功提交后** → 回到 Step 2。

**`/run` 失败** → 进入修复循环（最多 5 次，同一错误 3 次停止）。

## Step 5: 收尾（停止）

当前 item 所有 F-N 完成后，dev-loop **结束**。不自动开发下一个 roadmap 节点。

1. item 文档头部 `**状态:** 进行中` → `**状态:** 完成`
2. 同步更新 roadmap 中对应的 checkbox
3. 打印:
   ```
   Item 完成: <名称>
   F-1~F-N 全部完成
   ```

## 违规检查清单

执行 dev-loop 时，以下行为是违规的：
- ❌ Step 3 不委派 autopilot，自己直接写代码
- ❌ autopilot 完成后直接改代码、写测试、修 lint
- ❌ Step 4 被跳过，直接进入下一个 F-N
- ❌ 说"这个太简单了不需要 /run"

**Step 4 没有例外。1 行代码的改动也要跑 /run。**
