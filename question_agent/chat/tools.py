"""LangGraph tool functions wrapping the existing question-generation pipeline."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ExtractKnowledgePointsInput(BaseModel):
    """Schema for extract_knowledge_points tool input."""

    text: str = Field(description="需要提取知识点的教材文本内容")


@tool(args_schema=ExtractKnowledgePointsInput)
def extract_knowledge_points(text: str) -> str:
    """从教材文本中提取知识点。当用户提供了学习材料、课本内容、教学文本，并希望从中识别核心知识点时调用此工具。

    Args:
        text: 需要提取知识点的教材文本内容
    """
    from question_agent.knowledge import extract_knowledge_points_hybrid
    from question_agent.knowledge.models import ChapterWindow

    paragraphs = [{"text": line.strip()} for line in text.split("\n") if line.strip()]
    if not paragraphs:
        paragraphs = [{"text": text}] if text.strip() else []

    window = ChapterWindow(
        chapter_id="doc_full",
        chapter_title="Full Document",
        text=text,
        line_start=0,
        line_end=len(paragraphs),
    )

    result = extract_knowledge_points_hybrid([window], paragraphs)

    points = result.get("knowledge_points", [])
    output = []
    for kp in points:
        output.append(
            {
                "name": kp.name,
                "description": kp.description,
                "tags": [{"value": t.value, "category": t.category} for t in kp.tags],
                "confidence": kp.confidence,
                "method": kp.method,
            }
        )
    return json.dumps(output, ensure_ascii=False)


@tool
def generate_questions(knowledge_points_json: str) -> str:
    """根据知识点列表生成选择题题目。当用户希望基于知识点出题、生成测验题、制作练习题时调用此工具。

    Args:
        knowledge_points_json: 知识点 JSON 数组字符串，每项含 name、description、tags 字段
    """
    from question_agent.questions.generator import _KpInput, generate_questions

    try:
        kp_list = json.loads(knowledge_points_json)
    except json.JSONDecodeError:
        return json.dumps({"error": "无效的 JSON 格式"}, ensure_ascii=False)

    inputs = [
        _KpInput(name=kp["name"], description=kp["description"], tags=kp.get("tags", []))
        for kp in kp_list
    ]

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            questions, stats = pool.submit(asyncio.run, generate_questions(inputs)).result()
    else:
        questions, stats = asyncio.run(generate_questions(inputs))

    output = {
        "questions": [
            {
                "id": q.id,
                "stem_text": q.stem_text,
                "options": [{"label": o.label, "text": o.text} for o in q.options],
                "knowledge_point_name": q.knowledge_point_name,
                "question_type": q.question_type,
                "status": q.status,
            }
            for q in questions
        ],
        "stats": {"total": stats.total, "successful": stats.successful, "failed": stats.failed},
    }
    return json.dumps(output, ensure_ascii=False)


ALL_TOOLS: list[Any] = [extract_knowledge_points, generate_questions]
