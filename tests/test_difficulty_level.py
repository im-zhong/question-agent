"""Tests for difficulty level control in question generation."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from question_agent.questions.llm import _DIFFICULTY_INSTRUCTIONS, generate_question_llm
from question_agent.questions.models import DifficultyLevel, QuestionOption, QuestionStem


class TestDifficultyModel:
    def test_question_stem_has_difficulty_field(self) -> None:
        stem = QuestionStem(
            id=1,
            stem_text="Test?",
            options=[QuestionOption(label="A", text="A")],
            difficulty="basic",
            knowledge_point_name="KP",
            question_type="definition",
        )
        assert stem.difficulty == "basic"

    def test_question_stem_difficulty_defaults_intermediate(self) -> None:
        stem = QuestionStem(
            id=1,
            stem_text="Test?",
            options=[QuestionOption(label="A", text="A")],
            knowledge_point_name="KP",
            question_type="definition",
        )
        assert stem.difficulty == "intermediate"

    def test_difficulty_level_values(self) -> None:
        valid: list[DifficultyLevel] = ["basic", "intermediate", "advanced"]
        for d in valid:
            stem = QuestionStem(
                id=1,
                stem_text="Q?",
                options=[QuestionOption(label="A", text="A")],
                difficulty=d,
                knowledge_point_name="KP",
                question_type="definition",
            )
            assert stem.difficulty == d


class TestDifficultyInstructions:
    def test_all_difficulty_levels_have_instructions(self) -> None:
        for level in ("basic", "intermediate", "advanced"):
            assert level in _DIFFICULTY_INSTRUCTIONS
            assert len(_DIFFICULTY_INSTRUCTIONS[level]) > 0

    def test_instructions_contain_level_keyword(self) -> None:
        for level in ("basic", "intermediate", "advanced"):
            assert level.upper() in _DIFFICULTY_INSTRUCTIONS[level]


class TestDifficultyInLlm:
    def _make_mock_client(self) -> tuple[MagicMock, MagicMock]:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "stem_text": "Test question?",
                "correct_answer": "A",
                "options": [
                    {"label": "A", "text": "A"},
                    {"label": "B", "text": "B"},
                    {"label": "C", "text": "C"},
                    {"label": "D", "text": "D"},
                ],
            }
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        return mock_client, mock_response

    def test_basic_difficulty_in_prompt(self) -> None:
        mock_client, _ = self._make_mock_client()
        result = generate_question_llm(
            name="力",
            description="力是物体间的相互作用",
            difficulty="basic",
            client=mock_client,
        )
        assert result is not None
        assert result.difficulty == "basic"
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        assert "BASIC" in messages[0]["content"]

    def test_advanced_difficulty_in_prompt(self) -> None:
        mock_client, _ = self._make_mock_client()
        result = generate_question_llm(
            name="力",
            description="力是物体间的相互作用",
            difficulty="advanced",
            client=mock_client,
        )
        assert result is not None
        assert result.difficulty == "advanced"
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        assert "ADVANCED" in messages[0]["content"]

    def test_intermediate_difficulty_in_prompt_by_default(self) -> None:
        mock_client, _ = self._make_mock_client()
        result = generate_question_llm(
            name="力",
            description="力是物体间的相互作用",
            client=mock_client,
        )
        assert result is not None
        assert result.difficulty == "intermediate"
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        assert "INTERMEDIATE" in messages[0]["content"]

    def test_difficulty_instruction_appended_after_prompt(self) -> None:
        mock_client, _ = self._make_mock_client()
        generate_question_llm(
            name="力",
            description="力是物体间的相互作用",
            tags=[{"value": "力", "category": "concept"}],
            difficulty="basic",
            client=mock_client,
        )
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        content = messages[0]["content"]
        from question_agent.questions.prompts import PROMPT_REGISTRY

        base_prompt = PROMPT_REGISTRY["concept"]
        assert content.startswith(base_prompt)
        remainder = content[len(base_prompt) :].strip()
        assert remainder.startswith("Difficulty:")
