"""GLM-5 question generation via zai-sdk.

Generates structured question stems with 4 simplified options from
knowledge point inputs using semantic LLM analysis. Supports category-aware
prompt selection with few-shot examples per knowledge point type.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, ValidationError

from question_agent.chapters.llm import _create_client
from question_agent.config import settings
from question_agent.questions.models import QuestionOption, QuestionStem, QuestionType

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0
_TEMPERATURE = 0.7
_MAX_TOKENS = 2000

_JSON_SCHEMA = (
    '{"stem_text": "...", "options": [{"label": "A", "text": "..."}, '
    '{"label": "B", "text": "..."}, {"label": "C", "text": "..."}, '
    '{"label": "D", "text": "..."}]}'
)

_CONCEPT_PROMPT = f"""\
You are a definition/understanding question generator for educational content.

Strategy: Ask about the meaning, definition, or essential characteristics of \
a concept. The stem should contain words like "定义"(definition), "含义" \
(meaning), "是指" (refers to), or "以下哪个正确描述" (which correctly describes).

Rules:
1. The question must test understanding of the concept's definition or meaning.
2. Generate exactly 4 options labeled A, B, C, D.
3. Options are simplified placeholders — plausible but not carefully designed.
4. Return ONLY valid JSON — no commentary, no markdown fences.

Output JSON schema:
{_JSON_SCHEMA}

Example:
Input: "加速度" — 速度变化量与发生这一变化所用时间的比值
Output: {{"stem_text": "加速度的定义是指以下哪个？", "options": [\
{{"label": "A", "text": "速度变化量与时间的比值"}}, \
{{"label": "B", "text": "位移与时间的比值"}}, \
{{"label": "C", "text": "速度与时间的乘积"}}, \
{{"label": "D", "text": "力与质量的比值"}}]}}
"""

_FORMULA_PROMPT = f"""\
You are an application/calculation question generator for educational content.

Strategy: Create a problem that requires applying a formula or equation in a \
concrete scenario. The stem should include specific numerical values or a \
variable substitution context.

Rules:
1. The question must require applying the formula to solve a problem.
2. Generate exactly 4 options labeled A, B, C, D.
3. Options are simplified placeholders — plausible but not carefully designed.
4. Return ONLY valid JSON — no commentary, no markdown fences.

Output JSON schema:
{_JSON_SCHEMA}

Example:
Input: "牛顿第二定律 F=ma" — 力等于质量乘以加速度
Output: {{"stem_text": "一个质量为2kg的物体受到10N的合力作用，其加速度为多少？", \
"options": [{{"label": "A", "text": "5 m/s²"}}, \
{{"label": "B", "text": "20 m/s²"}}, \
{{"label": "C", "text": "8 m/s²"}}, \
{{"label": "D", "text": "12 m/s²"}}]}}
"""

_PROCEDURE_PROMPT = f"""\
You are a step/operation question generator for educational content.

Strategy: Ask about the correct sequence, steps, or operational procedure of \
a process. The stem should contain words like "步骤"(steps), "操作"(operation), \
"顺序"(order), or "以下哪个正确" (which is correct).

Rules:
1. The question must test knowledge of a procedure or process.
2. Generate exactly 4 options labeled A, B, C, D.
3. Options are simplified placeholders — plausible but not carefully designed.
4. Return ONLY valid JSON — no commentary, no markdown fences.

Output JSON schema:
{_JSON_SCHEMA}

Example:
Input: "科学实验的基本步骤" — 提出问题→作出假设→设计实验→收集数据→得出结论
Output: {{"stem_text": "科学实验的正确步骤顺序是？", "options": [\
{{"label": "A", "text": "提出问题→假设→实验→数据→结论"}}, \
{{"label": "B", "text": "实验→假设→数据→结论→问题"}}, \
{{"label": "C", "text": "结论→数据→实验→假设→问题"}}, \
{{"label": "D", "text": "假设→实验→问题→数据→结论"}}]}}
"""

_FACT_PROMPT = f"""\
You are a recall/fact question generator for educational content.

Strategy: Ask about factual information that should be memorized. The stem \
should contain words like "以下哪个"(which of the following), "是多少"(what is), \
or "属于"(belongs to).

Rules:
1. The question must test recall of a specific fact or piece of knowledge.
2. Generate exactly 4 options labeled A, B, C, D.
3. Options are simplified placeholders — plausible but not carefully designed.
4. Return ONLY valid JSON — no commentary, no markdown fences.

Output JSON schema:
{_JSON_SCHEMA}

Example:
Input: "光速" — 真空中光速约为3×10⁸ m/s
Output: {{"stem_text": "真空中光速的值约为？", "options": [\
{{"label": "A", "text": "3×10⁸ m/s"}}, \
{{"label": "B", "text": "3×10⁶ m/s"}}, \
{{"label": "C", "text": "3×10¹⁰ m/s"}}, \
{{"label": "D", "text": "3×10⁴ m/s"}}]}}
"""

_PRINCIPLE_PROMPT = f"""\
You are an analysis/derivation question generator for educational content.

Strategy: Ask about underlying principles, causal relationships, or require \
logical derivation. The stem should contain words like "原因"(reason), \
"为什么"(why), "推导"(derive), or "以下哪个分析正确" (which analysis is correct).

Rules:
1. The question must test understanding of a principle or require analysis.
2. Generate exactly 4 options labeled A, B, C, D.
3. Options are simplified placeholders — plausible but not carefully designed.
4. Return ONLY valid JSON — no commentary, no markdown fences.

Output JSON schema:
{_JSON_SCHEMA}

Example:
Input: "牛顿第三定律" — 作用力与反作用力大小相等、方向相反
Output: {{"stem_text": "根据牛顿第三定律，以下哪个分析正确？", "options": [\
{{"label": "A", "text": "作用力和反作用力大小相等方向相反"}}, \
{{"label": "B", "text": "作用力和反作用力方向相同"}}, \
{{"label": "C", "text": "作用力始终大于反作用力"}}, \
{{"label": "D", "text": "作用力和反作用力作用在同一物体上"}}]}}
"""

_GENERIC_PROMPT = f"""\
You are a question generation engine for educational content. Given a \
knowledge point, generate a multiple-choice question stem with 4 options.

Rules:
1. The question must be directly relevant to the knowledge point's name \
and description.
2. Generate exactly 4 options labeled A, B, C, D.
3. Options are simplified placeholders — plausible but not carefully designed.
4. Return ONLY valid JSON — no commentary, no markdown fences.

Output JSON schema:
{_JSON_SCHEMA}
"""

PROMPT_REGISTRY: dict[str, str] = {
    "concept": _CONCEPT_PROMPT,
    "formula": _FORMULA_PROMPT,
    "procedure": _PROCEDURE_PROMPT,
    "fact": _FACT_PROMPT,
    "principle": _PRINCIPLE_PROMPT,
}


def _select_prompt(tags: list[dict[str, str]] | None) -> str:
    """Select the appropriate system prompt based on the primary tag category."""
    if tags and tags[0]["category"] in PROMPT_REGISTRY:
        return PROMPT_REGISTRY[tags[0]["category"]]
    return _GENERIC_PROMPT


class _LlmQuestionResult(BaseModel):
    stem_text: str
    options: list[QuestionOption]


def _build_user_prompt(
    name: str, description: str, tags: list[dict[str, str]] | None = None
) -> str:
    """Build a user prompt from a knowledge point."""
    parts = [f"Knowledge point name: {name}", f"Description: {description}"]
    if tags:
        tag_strs = [f"{t['value']}({t['category']})" for t in tags]
        parts.append(f"Tags: {', '.join(tag_strs)}")
    return "\n".join(parts)


def _parse_response(raw: str) -> _LlmQuestionResult | None:
    """Parse GLM-5 JSON response into question result."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        data = json.loads(text)
        return _LlmQuestionResult.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        logger.warning("GLM-5 returned invalid JSON for question generation: %.200s", raw)
        return None


def generate_question_llm(
    name: str,
    description: str,
    tags: list[dict[str, str]] | None = None,
    client: Any = None,
) -> QuestionStem | None:
    """Use GLM-5 to generate a question from a knowledge point.

    Args:
        name: Knowledge point name.
        description: Knowledge point description.
        tags: Optional tag list with value and category fields.
        client: Optional pre-configured ZhipuAiClient (for testing).

    Returns:
        QuestionStem with LLM-generated content, or None if unavailable.
    """
    if not name.strip():
        return None

    if client is None:
        client = _create_client()

    if client is None:
        return None

    system_prompt = _select_prompt(tags)

    try:
        response = client.chat.completions.create(
            model=settings.glm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": _build_user_prompt(name, description, tags)},
            ],
            temperature=_TEMPERATURE,
            max_tokens=_MAX_TOKENS,
            response_format={"type": "json_object"},
            timeout=_TIMEOUT,
        )
    except Exception as e:
        logger.warning("GLM-5 API call failed for question generation: %s", e)
        return None

    content = response.choices[0].message.content if response.choices else ""
    if not content:
        return None

    result = _parse_response(content)
    if result is None:
        return None

    category = tags[0]["category"] if tags else "concept"
    qtype = category_to_question_type(category)

    return QuestionStem(
        id=0,  # caller assigns IDs
        stem_text=result.stem_text,
        options=result.options,
        knowledge_point_name=name,
        question_type=qtype,
    )


def category_to_question_type(category: str) -> QuestionType:
    mapping: dict[str, QuestionType] = {
        "concept": "definition",
        "formula": "calculation",
        "procedure": "procedure",
        "fact": "recall",
        "principle": "analysis",
    }
    return mapping.get(category, "definition")
