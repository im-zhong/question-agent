"""Edge case tests for questions/generator.py and questions/prompts.py modules."""

import json
from unittest.mock import MagicMock

import pytest

from question_agent.questions.generator import _KpInput, _make_failed_stem, generate_questions
from question_agent.questions.llm import generate_question_llm
from question_agent.questions.prompts import PROMPT_REGISTRY, select_prompt


class TestSelectPromptEdgeCases:
    def test_empty_tags_list_returns_generic(self) -> None:
        from question_agent.questions.prompts import _GENERIC_PROMPT

        assert select_prompt([]) == _GENERIC_PROMPT

    def test_tags_with_empty_category(self) -> None:
        from question_agent.questions.prompts import _GENERIC_PROMPT

        assert select_prompt([{"value": "x", "category": ""}]) == _GENERIC_PROMPT

    def test_tags_with_none_value_in_category(self) -> None:
        result = select_prompt([{"value": "test", "category": "concept"}])
        assert result == PROMPT_REGISTRY["concept"]

    def test_all_prompts_contain_json_schema(self) -> None:
        for cat, prompt in PROMPT_REGISTRY.items():
            assert "stem_text" in prompt, f"Category {cat} prompt missing stem_text in schema"
            assert "options" in prompt, f"Category {cat} prompt missing options in schema"


class TestMakeFailedStemEdgeCases:
    def test_no_tags_defaults_to_concept(self) -> None:
        kp = _KpInput(name="test", description="desc", tags=[])
        stem = _make_failed_stem(1, kp)
        assert stem.question_type == "definition"
        assert stem.status == "failed"
        assert stem.id == 1

    def test_formula_tag_gives_calculation_type(self) -> None:
        kp = _KpInput(name="test", description="desc", tags=[{"value": "x", "category": "formula"}])
        stem = _make_failed_stem(5, kp)
        assert stem.question_type == "calculation"
        assert stem.id == 5

    def test_failed_stem_has_four_options(self) -> None:
        kp = _KpInput(name="test", description="desc", tags=[])
        stem = _make_failed_stem(1, kp)
        assert len(stem.options) == 4
        labels = [o.label for o in stem.options]
        assert labels == ["A", "B", "C", "D"]


class TestGenerateQuestionsEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_list_returns_empty(self) -> None:
        questions, stats = await generate_questions([])
        assert questions == []
        assert stats.total == 0
        assert stats.successful == 0
        assert stats.failed == 0

    @pytest.mark.asyncio
    async def test_all_fail_gives_all_failed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "question_agent.questions.generator.generate_question_llm", lambda **kw: None
        )
        kps = [
            _KpInput(name=f"kp{i}", description=f"desc{i}", tags=[])
            for i in range(3)
        ]
        questions, stats = await generate_questions(kps)
        assert stats.total == 3
        assert stats.failed == 3
        assert stats.successful == 0
        for q in questions:
            assert q.status == "failed"

    @pytest.mark.asyncio
    async def test_single_knowledge_point(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from question_agent.questions.models import QuestionOption, QuestionStem

        mock_stem = QuestionStem(
            id=0,
            stem_text="test question",
            options=[
                QuestionOption(label="A", text="a"),
                QuestionOption(label="B", text="b"),
                QuestionOption(label="C", text="c"),
                QuestionOption(label="D", text="d"),
            ],
            knowledge_point_name="test",
            question_type="definition",
        )
        monkeypatch.setattr(
            "question_agent.questions.generator.generate_question_llm",
            lambda **kw: mock_stem,
        )
        questions, stats = await generate_questions(
            [_KpInput(name="test", description="desc", tags=[])]
        )
        assert stats.total == 1
        assert stats.successful == 1
        assert questions[0].status == "success"

    @pytest.mark.asyncio
    async def test_mixed_success_and_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from question_agent.questions.models import QuestionOption, QuestionStem

        call_count = 0

        def _mock_gen(**kwargs: object) -> QuestionStem | None:
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                return None
            return QuestionStem(
                id=0,
                stem_text="q",
                options=[QuestionOption(label="A", text="a")] * 4,
                knowledge_point_name="test",
                question_type="definition",
            )

        monkeypatch.setattr(
            "question_agent.questions.generator.generate_question_llm", _mock_gen
        )
        kps = [_KpInput(name=f"kp{i}", description="d", tags=[]) for i in range(4)]
        questions, stats = await generate_questions(kps)
        assert stats.total == 4
        assert stats.successful == 2
        assert stats.failed == 2

    @pytest.mark.asyncio
    async def test_ids_are_sequential(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "question_agent.questions.generator.generate_question_llm", lambda **kw: None
        )
        kps = [_KpInput(name=f"kp{i}", description="d", tags=[]) for i in range(3)]
        questions, _ = await generate_questions(kps)
        assert [q.id for q in questions] == [1, 2, 3]
