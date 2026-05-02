---
iteration: 3
phase: "教材知识抽取 — 知识点识别与标注"
date: 2026-05-01
status: complete
previous: docs/superpowers/summaries/2026-05-01-summary.md
---

# 总结报告 — 2026-05-01 (Iteration 3)

## A. 本轮完成

- **知识点数据模型与窗口切分 (F-1):** `KnowledgePoint` + `KnowledgeTag` Pydantic 模型，`ChapterWindow` 辅助类型，`build_chapter_windows()` 按段落边界自动切分超大章节。按 plan 完成。
- **GLM-5 知识点提取 (F-2):** zai-sdk 复用 chapters/llm.py 模式，system prompt 定义五类知识点（概念/公式/步骤/事实/原理），JSON mode + temperature=0.1，max_tokens=3000。不可用时返回 None 不崩溃。按 plan 完成。
- **规则辅助检测 (F-3):** 标记词模式匹配（"定义：""称为""是指""公式：""定理"等），零成本初筛，confidence=0.7。plan 标注为"过度项"——为 LLM 降级兜底。按 plan 完成。
- **混合引擎 (F-4):** 规则+LLM 按 source_line 范围去重、置信度择优，降级为 rule_only/llm_only/none。按 plan 完成。
- **API 端点 (F-5):** `POST /knowledge` 端点，上传文件→提取→章节识别→知识点提取全管线。无章节时对全文做单窗口提取。按 plan 完成。
- **模块封装 (F-6):** `knowledge/` 子包 6 文件独立，main.py 仅调用公共接口。偏差：`__init__.py` 导出 5 个符号（含 ChapterWindow），与 chapters/ 一致的模块化模式。按 plan 完成。
- **集成测试基础设施:** conftest.py、fixtures 目录、markers、flow tests、walkthrough tests（4 新文件）。偏差：plan 未包含此项，属本轮追加。
- **Logging 工具链:** stdlib logging 加入 toolchain Phase 1，scaffold Tier B 增加 logging 配置步骤。按 plan 完成。
- **技能改进:** progressive-plan 增加 MVP/原型驱动垂直切片原则，run-skill 增加 Step 6 walkthrough gate，summarize 重构为内联 skill。

## B. 代码变更

| 文件 | +行 | -行 | 说明 |
|------|-----|-----|------|
| question_agent/knowledge/ (6 文件) | ~592 | 0 | 新增：知识点识别子包（models/detector/llm/hybrid/windows） |
| question_agent/main.py | +187 | ~5 | POST /knowledge 端点 + Pydantic 响应模型 |
| tests/test_knowledge_*.py (5 文件) | ~1001 | 0 | 新增：75 个知识点测试 |
| tests/integration/ (4 文件) | ~194 | 0 | 新增：conftest/fixtures/flow/walkthrough |
| .harness/ai-question-agent-toolchain.md | +21 | ~5 | 增加 stdlib logging + Walkthrough 配置 |

核心架构变更：新增 `knowledge/` 包实现"窗口切分→规则检测→LLM 提取→混合合并"四阶段管线，消费 chapters/ 的 ChapterNode 作为结构边界。API 从 3 端点扩展到 4 端点（/health + /extract + /structure + /knowledge）。

## C. 文档现状

| 文档类型 | 路径 | 状态 |
|----------|------|------|
| Spec | specs/2026-04-29-ai-question-agent.md | DRAFT — 已更新知识点模块和 /knowledge 端点 |
| Roadmap | plans/2026-04-29-ai-question-agent.md | 已更新 — 知识点识别标记完成 |
| Toolchain | .harness/ai-question-agent-toolchain.md | ACTIVE — stdlib logging 已加入 |
| Item | items/2026-05-01-01-知识点识别与标注.md | 完成 |
| State | state.md | 过时 — iteration 3 仍显示 pre-dev |

## D. 遗留问题

- **49 个旧测试 httpx.ConnectError 失败:** iterations 1-2 的测试（test_extract_pdf, test_extract_docx, test_smoke 等）全部因 httpx.ConnectError 失败，说明这些测试尝试连接真实服务器而非使用 in-process ASGI transport。knowledge/ 的新测试均正确使用 TestClient，全部通过。旧测试基础设施需修复。
- **Level 间隙自动补位仍未实现:** 从 iteration 2 遗留。hybrid.py 的 `_validate_level_sequence` 仍为占位。知识点提取依赖正确的层级结构，但当前不影响主流程。
- **zai-sdk 运行时依赖:** 从 iteration 2 遗留。_create_client() 对 ImportError 做了防御，但 pyproject.toml 未声明正式依赖。
- **跨窗口知识点截断:** 大章节切分为多窗口时，跨窗口知识点可能被截断。item 中记录了 overlap 区策略但未实现，依赖后处理去重。
- **纯文学科标记词覆盖低:** 规则检测对语文/英语教材几乎无效。已知局限，需 prompt 模板适配。

## E. 外部知识

- **FastAPI 集成测试最佳实践:** 社区共识是 `TestClient` + `pytest` + dependency overrides 为标准组合；`testcontainers-python` 可用于需要真实服务的场景。本项目当前 49 个测试失败正是未统一使用 TestClient 的问题。来源: testdriven.io, realpython.com, fastapi.tiangolo.com
- **Python structured logging:** `structlog` 是最流行的结构化日志方案，可与 stdlib 无缝集成；纯 stdlib 方案可用 custom Formatter + extra dict。本项目选用 stdlib logging（零依赖），后续如需 JSON 输出可引入 structlog。来源: Python stdlib docs, structlog 官方文档
- **AI 出题 SOTA:** 规则+LLM 混合方案在无标注数据场景下是工业界主流；RAG 在教育内容生成中越来越受关注；可控题目生成（难度/类型/知识点）是活跃研究方向。当前架构（规则兜底+LLM 主力）与此趋势一致。

## F. 下一轮建议

1. **优先修复 49 个 httpx.ConnectError 失败测试**，因为 CI 不可用意味着任何回归都无法自动捕获——这是当前最大的工程风险。具体做法：统一测试基础设施为 in-process ASGI TestClient（参照 knowledge/ 测试模式），或拆分为 unit（TestClient）和 integration（需服务器）两组。
2. **优先实现知识点层级关系构建（roadmap 下一项）**，因为知识点识别已完成，层级关系是知识抽取的最后一块拼图，完成后可进入出题引擎开发。
3. **补全 level 间隙处理策略**，因为知识点层级关系构建依赖正确的章节层级——缺失中间层级会将子知识点归入错误父节点。
4. **为知识点提取添加 overlap 区策略**，因为跨窗口截断会导致知识点描述不完整，影响下游出题质量。
5. **将 zai-sdk 加入 pyproject.toml 可选依赖**，从 iteration 2 遗留，静默降级风险持续存在。

## G. 量化统计

| 指标 | 数值 |
|------|------|
| 本轮 commits | 22（从 9e90b0e 到 398d9db） |
| 文件变更 | 37 files (+4801/-309) |
| 新增代码文件 | knowledge/ 6 文件 (592 行) + tests/ 5 文件 (1001 行) |
| 总测试数 | 206（131 存量 + 75 knowledge 新增） |
| knowledge 测试通过率 | 100%（75 passed, 0 failed） |
| 全量测试通过率 | 63.6%（131 passed, 49 failed — 均为旧测试 httpx 错误） |
| ruff check | 0 issues |
| mypy strict | 0 issues |

## H. 架构快照

```mermaid
graph TB
    subgraph API
        Health[/health]
        Extract[/extract]
        Structure[/structure]
        Knowledge[/knowledge]
    end
    subgraph Extractors
        PDF[pdf.py]
        DOCX[docx.py]
        TXT[text.py]
    end
    subgraph Chapters
        Det[detector.py]
        LLM_CH[llm.py — GLM-5]
        Hyb[hybrid.py]
        Tree[tree.py]
    end
    subgraph Knowledge_NEW["knowledge/ (NEW)"]
        Win[windows.py<br>chapter → text windows]
        KDet[detector.py<br>rule-based]
        KLLM[llm.py<br>GLM-5 extraction]
        KHyb[hybrid.py<br>merge + degrade]
    end
    PDF --> Extract
    DOCX --> Extract
    TXT --> Extract
    Extract --> Structure
    Structure --> Det
    Structure --> LLM_CH
    Det --> Hyb
    LLM_CH --> Hyb
    Hyb --> Tree
    Tree --> Structure
    Structure --> Knowledge
    Knowledge --> Win
    Win --> KDet
    Win --> KLLM
    KDet --> KHyb
    KLLM --> KHyb
    KHyb --> Knowledge

    style Knowledge_NEW fill:#d4edda,stroke:#28a745
    style Win fill:#d4edda,stroke:#28a745
    style KDet fill:#d4edda,stroke:#28a745
    style KLLM fill:#d4edda,stroke:#28a745
    style KHyb fill:#d4edda,stroke:#28a745
    style Knowledge fill:#fff3cd,stroke:#ffc107
```

本轮新增 `knowledge/` 包（绿色）和 `/knowledge` 端点（黄色）。knowledge/ 消费 chapters/ 的 ChapterNode 作为输入窗口边界，形成"提取→章节→知识点"三层管线。

## J. 关键决策

**决定 1: 知识点提取采用"章节窗口"而非"全文一次性"策略**
- 原因: GLM-5 上下文窗口虽大（128K tokens），但单次推理的知识点密度过高会导致遗漏；按章节边界切分（max_chars=3000）既保持上下文聚焦，又控制 token 用量。
- 后果: 需要处理跨窗口知识点截断问题（overlap 区策略），但换来了更高的提取精度和更低的 API 成本。

**决定 2: 规则检测标记为"过度项"但仍实现**
- 原因: 规则检测覆盖面有限（仅对有明确标记词的文本有效），但为 GLM-5 不可用场景提供零成本兜底。confidence=0.7 确保 LLM 结果优先。
- 后果: 增加了代码量（detector.py ~102 行），但混合引擎的降级路径更完整。文科教材仍依赖 LLM。

**决定 3: 集成测试与单元测试分开目录**
- 原因: 单元测试用 TestClient（无需服务器），集成测试需要运行中的服务器。分开后可用 `--ignore=tests/integration/` 跳过。
- 后果: CI 可分阶段运行，但旧测试（iterations 1-2）未遵循此约定，导致 49 个失败。

## K. 经验教训

✅ **比预期顺利:**
- knowledge/ 复用 chapters/ 的架构模式（models/llm/detector/hybrid）极其顺畅——模板化的模块结构显著降低了设计决策负担
- 75 个 knowledge 测试首次运行全部通过，TestClient 模式验证了 in-process ASGI transport 的可靠性

⚠️ **比预期困难:**
- 旧测试的 httpx.ConnectError 失败比预期严重——49 个失败测试意味着迭代 1-2 的测试基础设施存在系统性问题，不是偶发的
- 知识点 prompt 调试比章节识别更复杂——知识点边界比章节边界模糊得多，"什么是知识点"比"什么是章节标题"更难定义

💡 **意外发现:**
- build_chapter_windows 的段落边界切分逻辑比预期重要——最初以为 max_chars=3000 只是简单截断，实际上按段落边界切分 + 空章节跳过需要仔细处理边界情况
- integration/ 目录的 conftest.py 与根 conftest.py 的 pytest 作用域规则需要显式配置，否则 fixture 不被发现
