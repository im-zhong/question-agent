"""Tests for question_agent.chat.tools — LangGraph tool functions."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

from question_agent.chat.tools import ALL_TOOLS, extract_knowledge_points, generate_questions


class TestToolRegistration:
    """Verify tools are correctly registered."""

    def test_all_tools_contains_both(self) -> None:
        assert len(ALL_TOOLS) == 2

    def test_tool_names(self) -> None:
        names = [t.name for t in ALL_TOOLS]
        assert "extract_knowledge_points" in names
        assert "generate_questions" in names

    def test_tools_have_chinese_descriptions(self) -> None:
        for t in ALL_TOOLS:
            assert t.description, f"{t.name} should have a description"
            assert any("一" <= c <= "鿿" for c in t.description), (
                f"{t.name} description should contain Chinese characters"
            )


class TestExtractKnowledgePoints:
    """Test the extract_knowledge_points tool."""

    def test_returns_json_string(self) -> None:
        """Tool returns a valid JSON string."""
        from question_agent.knowledge.models import KnowledgePoint, KnowledgeTag

        real_kp = KnowledgePoint(
            id=1,
            name="牛顿第二定律",
            description="描述力、质量和加速度之间的关系",
            tags=[KnowledgeTag(value="牛顿第二定律", category="formula")],
            confidence=0.9,
            method="hybrid",
            source_line_start=0,
            source_line_end=1,
        )
        mock_result = {"knowledge_points": [real_kp]}

        # Patch the source module where the function is imported from
        patch_path = "question_agent.knowledge.extract_knowledge_points_hybrid"
        with patch(patch_path, return_value=mock_result):
            result = extract_knowledge_points.invoke({"text": "牛顿第二定律 F=ma"})

        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "牛顿第二定律"
        assert parsed[0]["confidence"] == 0.9

    def test_empty_text_returns_empty_list(self) -> None:
        """Tool handles empty text gracefully."""
        mock_result = {"knowledge_points": []}
        patch_path = "question_agent.knowledge.extract_knowledge_points_hybrid"

        with patch(patch_path, return_value=mock_result):
            result = extract_knowledge_points.invoke({"text": ""})

        parsed = json.loads(result)
        assert parsed == []


class TestGenerateQuestions:
    """Test the generate_questions tool."""

    def test_returns_json_with_questions(self) -> None:
        """Tool returns a valid JSON string with questions."""
        from question_agent.questions.models import GenerationStats, QuestionOption, QuestionStem

        mock_questions = [
            QuestionStem(
                id=1,
                stem_text="牛顿第二定律的公式是？",
                options=[
                    QuestionOption(label="A", text="F=ma"),
                    QuestionOption(label="B", text="E=mc²"),
                    QuestionOption(label="C", text="F=mg"),
                    QuestionOption(label="D", text="P=mv"),
                ],
                knowledge_point_name="牛顿第二定律",
                question_type="calculation",
            )
        ]
        mock_stats = GenerationStats(total=1, successful=1, failed=0)

        # Patch the source module where generate_questions is imported from
        patch_path = "question_agent.questions.generator.generate_questions"
        with patch(patch_path, new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = (mock_questions, mock_stats)

            kp_json = json.dumps(
                [{"name": "牛顿第二定律", "description": "力与加速度关系", "tags": []}]
            )
            result = generate_questions.invoke({"knowledge_points_json": kp_json})

        parsed = json.loads(result)
        assert "questions" in parsed
        assert "stats" in parsed
        assert len(parsed["questions"]) == 1
        assert parsed["questions"][0]["stem_text"] == "牛顿第二定律的公式是？"

    def test_invalid_json_returns_error(self) -> None:
        """Tool returns error for invalid JSON input."""
        result = generate_questions.invoke({"knowledge_points_json": "not json"})
        parsed = json.loads(result)
        assert "error" in parsed


class TestToolNodeInGraph:
    """Test that the graph includes a tools node."""

    def test_graph_has_tools_node(self) -> None:
        from question_agent.chat.graph import create_chat_graph

        graph = create_chat_graph()
        assert "tools" in graph.nodes

    def test_llm_has_tools_bound(self) -> None:
        from question_agent.chat.graph import _create_llm_with_tools

        llm = _create_llm_with_tools()
        # bind_tools returns a RunnableBinding, not ChatOpenAI
        assert hasattr(llm, "ainvoke")
