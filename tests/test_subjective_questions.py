"""Tests for subjective question generation (short_answer and essay)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from question_agent.questions.llm import generate_question_llm
from question_agent.questions.models import QuestionStem
from question_agent.questions.prompts import QUESTION_TYPE_REGISTRY, select_prompt


class TestSubjectivePrompts:
    def test_short_answer_prompt_in_registry(self) -> None:
        assert "short_answer" in QUESTION_TYPE_REGISTRY

    def test_essay_prompt_in_registry(self) -> None:
        assert "essay" in QUESTION_TYPE_REGISTRY

    def test_select_prompt_with_short_answer_type(self) -> None:
        prompt = select_prompt(None, question_type="short_answer")
        assert prompt == QUESTION_TYPE_REGISTRY["short_answer"]

    def test_select_prompt_with_essay_type(self) -> None:
        prompt = select_prompt(None, question_type="essay")
        assert prompt == QUESTION_TYPE_REGISTRY["essay"]

    def test_select_prompt_ignores_type_when_tags_match(self) -> None:
        """When question_type is None, tags determine the prompt."""
        prompt = select_prompt([{"value": "v", "category": "concept"}])
        assert "definition" in prompt.lower() or "understanding" in prompt.lower()

    def test_select_prompt_type_overrides_tags(self) -> None:
        """When question_type is set, it overrides tag-based selection."""
        prompt = select_prompt([{"value": "v", "category": "concept"}], question_type="essay")
        assert prompt == QUESTION_TYPE_REGISTRY["essay"]

    def test_short_answer_prompt_has_reference_answer(self) -> None:
        assert "reference_answer" in QUESTION_TYPE_REGISTRY["short_answer"]

    def test_essay_prompt_has_reference_answer(self) -> None:
        assert "reference_answer" in QUESTION_TYPE_REGISTRY["essay"]


class TestSubjectiveLlmGeneration:
    def _make_mock_client(self) -> tuple[MagicMock, MagicMock]:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "stem_text": "请简述牛顿第二定律的内容。",
                "reference_answer": (
                    "牛顿第二定律指出物体的加速度与所受合力成正比，与质量成反比，即 F=ma。"
                ),
                "options": [],
            }
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        return mock_client, mock_response

    def test_short_answer_generation(self) -> None:
        mock_client, _ = self._make_mock_client()
        result = generate_question_llm(
            name="牛顿第二定律",
            description="F=ma",
            question_type="short_answer",
            client=mock_client,
        )
        assert result is not None
        assert result.question_type == "short_answer"
        assert result.reference_answer is not None
        assert result.options == []

    def test_essay_generation(self) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "stem_text": "试论述牛顿三大定律的内在联系。",
                "reference_answer": "三大定律构成完整力学体系...",
                "options": [],
            }
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        result = generate_question_llm(
            name="牛顿定律",
            description="三大运动定律",
            question_type="essay",
            client=mock_client,
        )
        assert result is not None
        assert result.question_type == "essay"
        assert result.reference_answer is not None

    def test_subjective_uses_correct_prompt(self) -> None:
        mock_client, _ = self._make_mock_client()
        generate_question_llm(
            name="力",
            description="力是物体间的相互作用",
            question_type="short_answer",
            client=mock_client,
        )
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        content = messages[0]["content"]
        assert "reference_answer" in content
        assert "short-answer" in content.lower() or "brief" in content.lower()


class TestQuestionTypeModel:
    def test_short_answer_is_valid_type(self) -> None:
        stem = QuestionStem(
            id=1,
            stem_text="请简述加速度的定义。",
            options=[],
            reference_answer="加速度是速度变化率。",
            knowledge_point_name="加速度",
            question_type="short_answer",
        )
        assert stem.question_type == "short_answer"
        assert stem.reference_answer is not None

    def test_essay_is_valid_type(self) -> None:
        stem = QuestionStem(
            id=1,
            stem_text="论述牛顿力学体系。",
            options=[],
            reference_answer="牛顿力学体系包括...",
            knowledge_point_name="牛顿力学",
            question_type="essay",
        )
        assert stem.question_type == "essay"

    def test_reference_answer_defaults_none(self) -> None:
        stem = QuestionStem(
            id=1,
            stem_text="Q?",
            options=[],
            knowledge_point_name="KP",
            question_type="definition",
        )
        assert stem.reference_answer is None
