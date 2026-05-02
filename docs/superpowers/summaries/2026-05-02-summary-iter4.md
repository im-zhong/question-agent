---
iteration: 4
phase: "题目生成 — 基于知识点生成题干"
date: 2026-05-02
status: complete
previous: docs/superpowers/summaries/2026-05-01-summary-iter3.md
---

# 总结报告 — 2026-05-02 (Iteration 4)

## A. 本轮完成

- **题目数据模型与 API 骨架 (F-1):** `QuestionStem`/`QuestionOption` Pydantic 模型 + `POST /questions/generate` 骨架端点。按 plan 完成。
- **端到端出题原型 (F-2):** GLM-5 出题 prompt + JSON mode 解析 + placeholder fallback。打通"知识点→LLM→题干+4选项"全链路。按 plan 完成。
- **知识点类别感知生成 (F-3):** 5 类 category→prompt 映射（concept/formula/procedure/fact/principle），每类含策略描述 + few-shot 示例。按 plan 完成。
- **多知识点批量生成 (F-4):** 批量请求支持，`generation_stats`（total/successful/failed）+ 单条失败隔离（status="failed" + 占位题干）。按 plan 完成。
- **文件上传出题管线 (F-5):** `POST /questions/generate/from-file`，一步到位运行 提取→章节→知识点→题干 全管线。响应含 chapters + knowledge_points + questions + generation_stats。按 plan 完成。
- **模块封装 (F-6):** questions/ 子包拆分为 models.py / llm.py / prompts.py / generator.py / __init__.py。main.py 出题路由仅调用 `generate_questions()` 公共接口，无内联逻辑。偏差：`_KpInput` 为 dataclass 非 Pydantic（避免与 main.py 的 Pydantic `KnowledgePointInput` 冲突）。按 plan 完成。
- **旧测试修复:** iteration 3 遗留的 49 个 httpx.ConnectError 失败全部修复，迁移到 ASGITransport + AsyncClient。偏差：plan 未包含，属本轮追加修复。

## B. 代码变更

| 文件 | +行 | -行 | 说明 |
|------|-----|-----|------|
| question_agent/questions/ (5 文件) | ~421 | 0 | 新增：出题子包（models/llm/prompts/generator） |
| question_agent/main.py | +262 | ~50 | 两个新端点 + 响应模型 + questions/ 公共 API 调用 |
| tests/test_questions_*.py (4 文件) | ~814 | 0 | 新增：出题端点 + from-file + LLM 模块测试 |
| tests/test_edge_*.py (3 新文件) | ~462 | 0 | 新增：questions/from-file/generator 边缘测试 |
| tests/ (旧测试修复) | ~0 | ~200 | 迁移到 ASGITransport，消除 httpx.ConnectError |

核心架构变更：新增 `questions/` 包实现"类别感知 prompt 选择→GLM-5 生成→JSON 解析→失败隔离→批量统计"出题管线。`generator.py` 提供异步批量生成入口，消费知识点输入产出题干列表。API 从 4 端点扩展到 6 端点（+/questions/generate + /questions/generate/from-file）。

## C. 文档现状

| 文档类型 | 路径 | 状态 |
|----------|------|------|
| Spec | specs/2026-04-29-ai-question-agent.md | DRAFT — 需更新出题模块和两个新端点 |
| Roadmap | plans/2026-04-29-ai-question-agent.md | 已更新 — 基于知识点生成题干标记完成 |
| Toolchain | .harness/ai-question-agent-toolchain.md | ACTIVE — 无需更新 |
| Item | items/2026-05-01-02-基于知识点生成题干.md | 完成 |
| State | state.md | 过时 — 需更新为 iteration 4 |

## D. 遗留问题

- **选项为简化占位，非合理干扰项:** 当前 4 个选项由 LLM 生成但未经干扰项逻辑建模，可能存在"明显错误选项"。roadmap 中干扰项生成为独立分支。
- **zai-sdk 运行时依赖:** 从 iteration 2 遗留。_create_client() 对 ImportError 做了防御，但 pyproject.toml 未声明正式依赖。
- **Level 间隙自动补位仍未实现:** 从 iteration 2 遗留。hybrid.py 的 `_validate_level_sequence` 仍为占位。
- **出题端点串行调用 GLM-5:** generate_questions() 逐个 await asyncio.to_thread，多知识点时延迟线性增长。可改用 asyncio.gather 并行化。
- **from-file 端点与 knowledge 端点管线代码重复:** 提取→章节→窗口→知识点 的逻辑在两个端点中完全重复，应抽取为共享服务函数。

## E. 外部知识

- **正确答案生成最佳实践:** 业界共识是"先推理再生成答案"——Chain-of-Thought prompting + 独立验证调用可显著降低答案幻觉率。推荐两阶段管线：先生成题干+答案，再用独立 LLM 调用做反向验证。来源: arxiv.org (Automated QG Survey 2025), OpenAI Cookbook
- **干扰项生成 SOTA:** 两大主流方向：(1) 基于学生 misconception（常见错误）生成干扰项——迷惑性最强；(2) 基于知识图谱语义邻近节点生成概念混淆型干扰项——结构化程度高。推荐管线：正确答案→错误类型标签→按类型独立生成干扰项。来源: EMNLP 2023-2024 DGP/RankDistractor 系列
- **结构化输出最佳实践:** JSON mode + 明确 schema + temperature 0.3（事实性输出）是当前最可靠的 LLM 结构化输出方案。先生成正确答案再生成干扰项可避免干扰项污染答案。来源: Anthropic Prompt Engineering Guide, Pinecone RAG-QG

## F. 下一轮建议

1. **优先实现正确答案生成（roadmap 下一项）**，因为题干生成已完成，答案生成是出题管线的必要下游——没有正确答案的题目无法使用。建议采用两阶段管线：题干→正确答案（CoT + 低温度）→反向验证。
2. **干扰项逻辑建模应在正确答案之后**，因为干扰项必须围绕正确答案设计——先生成正确答案，再按错误类型标签（概念混淆/计算错误/推理偏差）生成每条干扰项。roadmap 中此项为独立分支。
3. **抽取 from-file 与 knowledge 的共享管线函数**，因为当前两处代码完全重复（~80 行），下一轮新增端点时重复问题会加剧。建议抽取 `_extract_knowledge_pipeline()` 内部函数。
4. **并行化 GLM-5 批量调用**，因为当前串行模式下 5 个知识点需要 ~10 秒，改用 asyncio.gather 可降至 ~2 秒。
5. **将 zai-sdk 加入 pyproject.toml 可选依赖**，从 iteration 2 遗留，静默降级风险持续存在。

## G. 量化统计

| 指标 | 数值 |
|------|------|
| 本轮 commits | 8（从 981e049 到 7f1fae7） |
| 文件变更 | 27 files (+2576/-431) |
| 新增代码文件 | questions/ 5 文件 (421 行) + tests/ 7 文件 (1276 行) |
| 总测试数 | 291（含 12 新增 generator/prompts 边缘测试） |
| 测试通过率 | 100%（291 passed, 0 failed） |
| 集成测试 | 9 passed（含 from-file walkthrough） |
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
        QGen[/questions/generate]
        QFile[/questions/generate/from-file]
    end
    subgraph Extractors
        PDF[pdf.py]
        DOCX[docx.py]
        TXT[text.py]
    end
    subgraph Chapters
        Det[detector.py]
        LLM_CH[llm.py]
        Hyb[hybrid.py]
        Tree[tree.py]
    end
    subgraph Knowledge
        Win[windows.py]
        KDet[detector.py]
        KLLM[llm.py]
        KHyb[hybrid.py]
    end
    subgraph Questions_NEW["questions/ (NEW)"]
        QModels[models.py<br>QuestionStem/Option]
        QPrompts[prompts.py<br>5 category prompts]
        QLLM[llm.py<br>GLM-5 generation]
        QGenMod[generator.py<br>batch + fallback]
    end
    PDF --> Extract
    DOCX --> Extract
    TXT --> Extract
    Extract --> Structure
    Structure --> Det & LLM_CH
    Det & LLM_CH --> Hyb --> Tree
    Tree --> Knowledge
    Knowledge --> Win --> KDet & KLLM --> KHyb
    QGen --> QPrompts & QLLM & QGenMod
    QFile --> Win & KHyb & QGenMod

    style Questions_NEW fill:#d4edda,stroke:#28a745
    style QModels fill:#d4edda,stroke:#28a745
    style QPrompts fill:#d4edda,stroke:#28a745
    style QLLM fill:#d4edda,stroke:#28a745
    style QGenMod fill:#d4edda,stroke:#28a745
    style QGen fill:#fff3cd,stroke:#ffc107
    style QFile fill:#fff3cd,stroke:#ffc107
```

本轮新增 `questions/` 包（绿色）和两个出题端点（黄色）。questions/ 消费 knowledge/ 提取的知识点作为输入，generator.py 提供异步批量生成入口。/questions/generate/from-file 复用 knowledge 管线 + 出题管线。

## J. 关键决策

**决定 1: 出题 prompt 按知识点类别分发，而非统一 prompt**
- 原因: 不同类别的知识点适合不同的出题策略——概念类适合定义理解题，公式类适合应用计算题，统一 prompt 会导致出题方向与知识点不匹配。
- 后果: PROMPT_REGISTRY 维护 5+1 个 prompt 模板，新增类别时需扩展。但出题质量显著提升，few-shot 示例提供稳定输出格式。

**决定 2: 生成失败时返回占位题干而非跳过**
- 原因: 批量生成场景下，调用方需要与输入等长的输出列表来对应每个知识点。跳过会导致索引对不上。
- 后果: 失败条目带 status="failed" + 占位选项，调用方可按 status 过滤。占位逻辑封装在 generator.py 的 `_make_failed_stem()` 中。

**决定 3: 将 prompts.py 从 llm.py 中拆分出来**
- 原因: F-6 模块封装要求 questions/ 子包职责单一——prompts.py 管理 prompt 模板，llm.py 管理 API 调用，generator.py 管理批量编排。
- 后果: llm.py 通过 import 消费 prompts.py 的 `select_prompt()`，依赖方向清晰。测试也需分别 import。

## K. 经验教训

✅ **比预期顺利:**
- questions/ 复用 chapters/knowledge 的模块模式极其顺畅——models/llm/prompts/generator 四文件结构清晰
- 291 个测试首次全量通过，iteration 3 遗留的 49 个测试失败通过迁移到 ASGITransport 一并解决

⚠️ **比预期困难:**
- KnowledgePointInput 命名冲突——main.py 的 Pydantic 模型与 generator.py 的 dataclass 同名，ruff 报 F811。解决方案：内部 dataclass 改名为 _KpInput，仅导出 generate_questions 函数
- /questions/generate/from-file 与 /knowledge 管线代码重复度高（~80 行），重构为共享函数可减少维护负担但本轮未做

💡 **意外发现:**
- GLM-5 的 JSON mode 在出题场景比知识点提取场景更稳定——可能因为出题输出格式更简单（stem_text + 4 options）
- asyncio.to_thread 包装同步 SDK 调用的模式在 batch 场景下变成性能瓶颈——串行等待每个 LLM 调用完成，改用 asyncio.gather 可显著提升吞吐
