"""Tests for GLM-5 question generation module."""

import json
from unittest.mock import MagicMock

import pytest

from question_agent.questions.llm import (
    _build_user_prompt,
    _parse_response,
    category_to_question_type,
    generate_question_llm,
)
from question_agent.questions.models import QuestionStem
from question_agent.questions.prompts import PROMPT_REGISTRY, select_prompt


class TestBuildUserPrompt:
    def test_basic_prompt(self) -> None:
        result = _build_user_prompt("牛顿第二定律", "力等于质量乘以加速度")
        assert "牛顿第二定律" in result
        assert "力等于质量乘以加速度" in result

    def test_prompt_with_tags(self) -> None:
        tags = [{"value": "牛顿定律", "category": "formula"}]
        result = _build_user_prompt("牛顿第二定律", "desc", tags)
        assert "牛顿定律(formula)" in result

    def test_prompt_without_tags(self) -> None:
        result = _build_user_prompt("test", "desc", None)
        assert "Tags" not in result


class TestParseResponse:
    def test_valid_json(self) -> None:
        raw = json.dumps(
            {
                "stem_text": "关于牛顿第二定律，以下哪个表述正确？",
                "options": [
                    {"label": "A", "text": "F = ma"},
                    {"label": "B", "text": "F = mv"},
                    {"label": "C", "text": "F = mg"},
                    {"label": "D", "text": "F = mv²"},
                ],
            }
        )
        result = _parse_response(raw)
        assert result is not None
        assert "牛顿第二定律" in result.stem_text
        assert len(result.options) == 4
        assert result.options[0].label == "A"

    def test_markdown_fenced_json(self) -> None:
        data = {
            "stem_text": "关于加速度的定义",
            "options": [
                {"label": "A", "text": "速度变化量与时间的比值"},
                {"label": "B", "text": "位移与时间的比值"},
                {"label": "C", "text": "速度与时间的比值"},
                {"label": "D", "text": "力与质量的比值"},
            ],
        }
        raw = f"```json\n{json.dumps(data)}\n```"
        result = _parse_response(raw)
        assert result is not None
        assert "加速度" in result.stem_text

    def test_invalid_json_returns_none(self) -> None:
        result = _parse_response("not json at all")
        assert result is None

    def test_missing_options_returns_none(self) -> None:
        result = _parse_response(json.dumps({"stem_text": "test"}))
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        result = _parse_response("")
        assert result is None


class TestCategoryToQuestionType:
    def test_concept(self) -> None:
        assert category_to_question_type("concept") == "definition"

    def test_formula(self) -> None:
        assert category_to_question_type("formula") == "calculation"

    def test_procedure(self) -> None:
        assert category_to_question_type("procedure") == "procedure"

    def test_fact(self) -> None:
        assert category_to_question_type("fact") == "recall"

    def test_principle(self) -> None:
        assert category_to_question_type("principle") == "analysis"

    def test_unknown_defaults_to_definition(self) -> None:
        assert category_to_question_type("unknown") == "definition"


class TestGenerateQuestionLlm:
    def test_empty_name_returns_none(self) -> None:
        result = generate_question_llm("  ", "desc")
        assert result is None

    def test_no_api_key_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("question_agent.questions.llm._create_client", lambda: None)
        result = generate_question_llm("牛顿第二定律", "力等于质量乘以加速度")
        assert result is None

    def test_mock_llm_returns_question(self) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "stem_text": "牛顿第二定律的数学表达式是？",
                "options": [
                    {"label": "A", "text": "F = ma"},
                    {"label": "B", "text": "F = mv"},
                    {"label": "C", "text": "F = mg"},
                    {"label": "D", "text": "F = mgh"},
                ],
            }
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        result = generate_question_llm(
            name="牛顿第二定律",
            description="力等于质量乘以加速度",
            tags=[{"value": "牛顿第二定律", "category": "formula"}],
            client=mock_client,
        )
        assert result is not None
        assert isinstance(result, QuestionStem)
        assert "牛顿第二定律" in result.stem_text
        assert len(result.options) == 4
        assert result.options[0].label == "A"
        assert result.question_type == "calculation"
        assert result.knowledge_point_name == "牛顿第二定律"

    def test_mock_llm_invalid_json_returns_none(self) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "invalid json"
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        result = generate_question_llm(name="test", description="desc", client=mock_client)
        assert result is None

    def test_mock_llm_api_failure_returns_none(self) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")

        result = generate_question_llm(name="test", description="desc", client=mock_client)
        assert result is None

    def test_mock_llm_no_tags_defaults_to_definition(self) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "stem_text": "test question",
                "options": [
                    {"label": "A", "text": "a"},
                    {"label": "B", "text": "b"},
                    {"label": "C", "text": "c"},
                    {"label": "D", "text": "d"},
                ],
            }
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        result = generate_question_llm(name="test", description="desc", client=mock_client)
        assert result is not None
        assert result.question_type == "definition"


class TestPromptRegistry:
    def test_all_categories_have_prompts(self) -> None:
        for cat in ("concept", "formula", "procedure", "fact", "principle"):
            assert cat in PROMPT_REGISTRY
            assert len(PROMPT_REGISTRY[cat]) > 50

    def test_concept_prompt_contains_definition_keywords(self) -> None:
        prompt = PROMPT_REGISTRY["concept"]
        assert "定义" in prompt or "definition" in prompt.lower()

    def test_formula_prompt_contains_calculation_keywords(self) -> None:
        prompt = PROMPT_REGISTRY["formula"]
        assert "应用" in prompt or "calculation" in prompt.lower() or "数值" in prompt

    def test_procedure_prompt_contains_step_keywords(self) -> None:
        prompt = PROMPT_REGISTRY["procedure"]
        assert "步骤" in prompt or "step" in prompt.lower()

    def test_fact_prompt_contains_recall_keywords(self) -> None:
        prompt = PROMPT_REGISTRY["fact"]
        assert "识记" in prompt or "recall" in prompt.lower() or "事实" in prompt

    def test_principle_prompt_contains_analysis_keywords(self) -> None:
        prompt = PROMPT_REGISTRY["principle"]
        assert "分析" in prompt or "analysis" in prompt.lower() or "推导" in prompt

    def test_each_prompt_has_json_schema(self) -> None:
        for cat, prompt in PROMPT_REGISTRY.items():
            assert "stem_text" in prompt, f"{cat} prompt missing stem_text"
            assert "options" in prompt, f"{cat} prompt missing options"

    def test_each_prompt_has_few_shot_example(self) -> None:
        for cat, prompt in PROMPT_REGISTRY.items():
            assert "Example" in prompt or "示例" in prompt or "example" in prompt.lower()


class TestSelectPrompt:
    def test_concept_tag_selects_concept_prompt(self) -> None:
        tags = [{"value": "加速度", "category": "concept"}]
        prompt = select_prompt(tags)
        assert prompt == PROMPT_REGISTRY["concept"]

    def test_formula_tag_selects_formula_prompt(self) -> None:
        tags = [{"value": "F=ma", "category": "formula"}]
        prompt = select_prompt(tags)
        assert prompt == PROMPT_REGISTRY["formula"]

    def test_procedure_tag(self) -> None:
        tags = [{"value": "实验步骤", "category": "procedure"}]
        assert select_prompt(tags) == PROMPT_REGISTRY["procedure"]

    def test_fact_tag(self) -> None:
        tags = [{"value": "光速", "category": "fact"}]
        assert select_prompt(tags) == PROMPT_REGISTRY["fact"]

    def test_principle_tag(self) -> None:
        tags = [{"value": "牛顿第三定律", "category": "principle"}]
        assert select_prompt(tags) == PROMPT_REGISTRY["principle"]

    def test_no_tags_returns_generic(self) -> None:
        from question_agent.questions.prompts import _GENERIC_PROMPT

        assert select_prompt(None) == _GENERIC_PROMPT

    def test_unknown_category_returns_generic(self) -> None:
        from question_agent.questions.prompts import _GENERIC_PROMPT

        tags = [{"value": "x", "category": "unknown"}]
        assert select_prompt(tags) == _GENERIC_PROMPT

    def test_multi_tag_uses_primary(self) -> None:
        tags = [
            {"value": "牛顿定律", "category": "formula"},
            {"value": "牛顿定律", "category": "principle"},
        ]
        assert select_prompt(tags) == PROMPT_REGISTRY["formula"]


class TestCategoryAwareLlmGeneration:
    def test_concept_uses_concept_prompt(self) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "stem_text": "加速度的定义是什么？",
                "options": [
                    {"label": "A", "text": "速度变化量与时间的比值"},
                    {"label": "B", "text": "位移与时间的比值"},
                    {"label": "C", "text": "速度与时间的比值"},
                    {"label": "D", "text": "力与质量的比值"},
                ],
            }
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        result = generate_question_llm(
            name="加速度",
            description="速度变化量与时间的比值",
            tags=[{"value": "加速度", "category": "concept"}],
            client=mock_client,
        )
        assert result is not None
        assert result.question_type == "definition"
        # Verify the system prompt used was the concept one
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        assert messages[0]["content"] == PROMPT_REGISTRY["concept"]

    def test_formula_uses_formula_prompt(self) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "stem_text": "质量为5kg的物体受到20N力，加速度为？",
                "options": [
                    {"label": "A", "text": "4 m/s²"},
                    {"label": "B", "text": "100 m/s²"},
                    {"label": "C", "text": "25 m/s²"},
                    {"label": "D", "text": "15 m/s²"},
                ],
            }
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        result = generate_question_llm(
            name="牛顿第二定律",
            description="F=ma",
            tags=[{"value": "牛顿第二定律", "category": "formula"}],
            client=mock_client,
        )
        assert result is not None
        assert result.question_type == "calculation"
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        assert messages[0]["content"] == PROMPT_REGISTRY["formula"]


class TestLiveApi:
    @pytest.mark.asyncio
    async def test_live_api_question_generation(self) -> None:
        """Test against real GLM-5 API (skipped if no key)."""
        from question_agent.chapters.llm import _create_client

        client = _create_client()
        if client is None:
            pytest.skip("GLM_API_KEY not configured")

        result = generate_question_llm(
            name="牛顿第二定律",
            description="力等于质量乘以加速度",
            tags=[{"value": "牛顿第二定律", "category": "formula"}],
            client=client,
        )
        assert result is not None
        assert result.stem_text
        assert len(result.options) == 4
        assert result.knowledge_point_name == "牛顿第二定律"
