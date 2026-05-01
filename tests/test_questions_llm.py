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
