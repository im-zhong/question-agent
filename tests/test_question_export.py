"""Tests for /questions/export endpoint."""

from __future__ import annotations

from starlette.testclient import TestClient

from question_agent.main import app


def _sample_questions() -> list[dict]:
    return [
        {
            "id": 1,
            "stem_text": "什么是加速度？",
            "options": [
                {"label": "A", "text": "速度变化率"},
                {"label": "B", "text": "位移变化率"},
                {"label": "C", "text": "力与质量之比"},
                {"label": "D", "text": "速度与时间之比"},
            ],
            "correct_answer": "A",
            "difficulty": "basic",
            "knowledge_point_name": "加速度",
            "question_type": "definition",
            "status": "success",
            "error": None,
            "metadata": None,
        },
        {
            "id": 2,
            "stem_text": "F=ma 中 F 的单位是？",
            "options": [
                {"label": "A", "text": "牛顿"},
                {"label": "B", "text": "焦耳"},
                {"label": "C", "text": "帕斯卡"},
                {"label": "D", "text": "瓦特"},
            ],
            "correct_answer": "A",
            "difficulty": "intermediate",
            "knowledge_point_name": "牛顿第二定律",
            "question_type": "calculation",
            "status": "success",
            "error": None,
            "metadata": None,
        },
    ]


class TestQuestionExport:
    def test_export_markdown(self) -> None:
        """Export questions as Markdown."""
        with TestClient(app) as client:
            response = client.post(
                "/questions/export",
                json={"questions": _sample_questions(), "format": "markdown"},
            )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/markdown")
        text = response.text
        assert "什么是加速度？" in text
        assert "牛顿第二定律" in text
        assert "✓" in text
        assert "基础" in text
        assert "中等" in text

    def test_export_markdown_omits_failed(self) -> None:
        """Failed questions are skipped in Markdown export."""
        questions = _sample_questions()
        questions.append(
            {
                "id": 3,
                "stem_text": "失败题",
                "options": [{"label": "A", "text": "A"}],
                "correct_answer": None,
                "difficulty": "intermediate",
                "knowledge_point_name": "X",
                "question_type": "definition",
                "status": "failed",
                "error": "生成失败",
                "metadata": None,
            }
        )
        with TestClient(app) as client:
            response = client.post(
                "/questions/export",
                json={"questions": questions, "format": "markdown"},
            )
        assert response.status_code == 200
        assert "失败题" not in response.text

    def test_export_json_default(self) -> None:
        """Export questions as JSON when format is not markdown."""
        with TestClient(app) as client:
            response = client.post(
                "/questions/export",
                json={"questions": _sample_questions(), "format": "json"},
            )
        assert response.status_code == 200
        data = response.json()
        assert len(data["questions"]) == 2
        assert data["questions"][0]["stem_text"] == "什么是加速度？"

    def test_export_markdown_has_disposition_header(self) -> None:
        """Markdown export includes Content-Disposition header."""
        with TestClient(app) as client:
            response = client.post(
                "/questions/export",
                json={"questions": _sample_questions(), "format": "markdown"},
            )
        assert "attachment" in response.headers.get("content-disposition", "")
        assert "questions.md" in response.headers.get("content-disposition", "")
