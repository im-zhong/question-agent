"""Tests for correct_answer field in question generation."""

from __future__ import annotations

import json

from question_agent.questions.llm import _parse_response
from question_agent.questions.models import QuestionOption, QuestionStem
from question_agent.questions.prompts import _JSON_SCHEMA, PROMPT_REGISTRY


class TestCorrectAnswerModel:
    def test_question_stem_has_correct_answer_field(self) -> None:
        """QuestionStem model includes correct_answer field."""
        stem = QuestionStem(
            id=1,
            stem_text="Test question?",
            options=[
                QuestionOption(label="A", text="Option A"),
                QuestionOption(label="B", text="Option B"),
                QuestionOption(label="C", text="Option C"),
                QuestionOption(label="D", text="Option D"),
            ],
            correct_answer="A",
            knowledge_point_name="Test KP",
            question_type="definition",
        )
        assert stem.correct_answer == "A"

    def test_question_stem_correct_answer_defaults_none(self) -> None:
        """QuestionStem correct_answer defaults to None."""
        stem = QuestionStem(
            id=1,
            stem_text="Test?",
            options=[QuestionOption(label="A", text="A")],
            knowledge_point_name="KP",
            question_type="definition",
        )
        assert stem.correct_answer is None

    def test_question_stem_serialization_includes_correct_answer(self) -> None:
        """Serialized QuestionStem includes correct_answer."""
        stem = QuestionStem(
            id=1,
            stem_text="Q?",
            options=[QuestionOption(label="A", text="A")],
            correct_answer="B",
            knowledge_point_name="KP",
            question_type="definition",
        )
        data = stem.model_dump()
        assert "correct_answer" in data
        assert data["correct_answer"] == "B"


class TestLlmResultParsing:
    def test_parse_with_correct_answer(self) -> None:
        """Parse LLM response with correct_answer field."""
        raw = json.dumps(
            {
                "stem_text": "What is X?",
                "correct_answer": "A",
                "options": [
                    {"label": "A", "text": "Answer A"},
                    {"label": "B", "text": "Answer B"},
                    {"label": "C", "text": "Answer C"},
                    {"label": "D", "text": "Answer D"},
                ],
            }
        )
        result = _parse_response(raw)
        assert result is not None
        assert result.correct_answer == "A"
        assert result.stem_text == "What is X?"

    def test_parse_without_correct_answer(self) -> None:
        """Parse LLM response without correct_answer (backward compat)."""
        raw = json.dumps(
            {
                "stem_text": "What is X?",
                "options": [
                    {"label": "A", "text": "Answer A"},
                    {"label": "B", "text": "Answer B"},
                    {"label": "C", "text": "Answer C"},
                    {"label": "D", "text": "Answer D"},
                ],
            }
        )
        result = _parse_response(raw)
        assert result is not None
        assert result.correct_answer is None


class TestPromptSchema:
    def test_json_schema_includes_correct_answer(self) -> None:
        """The shared JSON schema includes correct_answer."""
        assert "correct_answer" in _JSON_SCHEMA

    def test_all_category_prompts_mention_correct_answer(self) -> None:
        """Every category prompt references correct_answer in rules or schema."""
        for name, prompt in PROMPT_REGISTRY.items():
            assert "correct_answer" in prompt, f"Prompt '{name}' missing correct_answer"

    def test_generic_prompt_mentions_correct_answer(self) -> None:
        """The generic prompt includes correct_answer rule."""
        from question_agent.questions.prompts import _GENERIC_PROMPT

        assert "correct_answer" in _GENERIC_PROMPT
