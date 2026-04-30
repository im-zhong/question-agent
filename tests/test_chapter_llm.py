"""Tests for GLM-5 chapter semantic recognition."""

from question_agent.chapters import ChapterHeading, LlmChapterResult, detect_chapters_llm
from question_agent.chapters.llm import _build_user_prompt, _create_client, _parse_response


class TestBuildUserPrompt:
    def test_includes_indices(self):
        paragraphs = [{"text": "First"}, {"text": "Second"}]
        result = _build_user_prompt(paragraphs)
        assert "[0]" in result
        assert "[1]" in result

    def test_includes_style_name(self):
        paragraphs = [{"text": "Title", "style_name": "Heading 1"}]
        result = _build_user_prompt(paragraphs)
        assert "[style=Heading 1]" in result

    def test_no_style_when_missing(self):
        paragraphs = [{"text": "Plain"}]
        result = _build_user_prompt(paragraphs)
        assert "[style=" not in result


class TestParseResponse:
    def test_valid_json(self):
        raw = '{"chapters": [{"title": "Intro", "level": 1, "start_index": 0, "end_index": 5}]}'
        result = _parse_response(raw)
        assert result is not None
        assert len(result) == 1
        assert isinstance(result[0], LlmChapterResult)
        assert result[0].title == "Intro"
        assert result[0].level == 1

    def test_multiple_chapters(self):
        raw = (
            '{"chapters": ['
            '{"title": "Ch1", "level": 1, "start_index": 0, "end_index": 3},'
            '{"title": "Ch2", "level": 1, "start_index": 3, "end_index": 7}'
            "]}"
        )
        result = _parse_response(raw)
        assert len(result) == 2

    def test_markdown_fenced_json(self):
        raw = '```json\n{"chapters": []}\n```'
        result = _parse_response(raw)
        assert result == []

    def test_invalid_json_returns_none(self):
        assert _parse_response("not json") is None

    def test_missing_chapters_key(self):
        assert _parse_response('{"other": []}') is None

    def test_empty_string(self):
        assert _parse_response("") is None


class TestCreateClient:
    def test_returns_client_when_key_configured(self):
        client = _create_client()
        assert client is not None

    def test_client_has_chat_method(self):
        client = _create_client()
        assert client is not None
        assert hasattr(client, "chat")


class TestDetectChaptersLlm:
    def test_empty_paragraphs_returns_none(self):
        result = detect_chapters_llm([])
        assert result is None

    def test_no_api_key_returns_none(self, monkeypatch):
        monkeypatch.setattr("question_agent.chapters.llm.settings.glm_api_key", "")
        result = detect_chapters_llm([{"text": "test"}])
        assert result is None

    def test_returns_chapter_headings(self):
        """Live test: send a non-standard numbered text to GLM-5."""
        paragraphs = [
            {"text": "Module 1: Introduction to Grammar"},
            {"text": "This module covers basic grammar concepts."},
            {"text": "Topic A: Nouns and Verbs"},
            {"text": "Nouns are naming words. Verbs are action words."},
            {"text": "Module 2: Sentence Structure"},
            {"text": "We now look at how sentences are built."},
        ]
        result = detect_chapters_llm(paragraphs)
        assert result is not None, "GLM-5 API should be available"
        assert len(result) >= 2, f"Expected at least 2 chapters, got {result}"
        for h in result:
            assert isinstance(h, ChapterHeading)
            assert h.method == "llm"
            assert h.confidence == 0.85
            assert h.level in (1, 2, 3)
            assert h.line_index >= 0

    def test_section_symbol_text(self):
        """Live test: non-Chinese section symbol numbering."""
        paragraphs = [
            {"text": "§1 Overview"},
            {"text": "Some introduction text here."},
            {"text": "§2.3 Force and Motion"},
            {"text": "Newton's laws are fundamental."},
        ]
        result = detect_chapters_llm(paragraphs)
        assert result is not None, "GLM-5 API should be available"
        assert len(result) >= 2

    def test_module_numbering(self):
        """Live test: Module/Unit style numbering."""
        paragraphs = [
            {"text": "Unit 5: Ecology"},
            {"text": "This unit explores ecosystems."},
            {"text": "Lesson 5.1: Food Chains"},
            {"text": "A food chain shows energy flow."},
            {"text": "Lesson 5.2: Habitats"},
            {"text": "Different organisms live in different habitats."},
        ]
        result = detect_chapters_llm(paragraphs)
        assert result is not None, "GLM-5 API should be available"
        assert len(result) >= 2
        levels = {r.level for r in result}
        # Unit 5 should be level 1, Lessons should be level 2
        assert 1 in levels
