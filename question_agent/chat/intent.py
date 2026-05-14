"""Intent classification for chat dispatch node."""

from __future__ import annotations

from typing import Literal

IntentType = Literal["extract", "generate", "chat"]

_EXTRACT_MIN_LENGTH = 200

_GENERATE_KEYWORDS = (
    "出题",
    "生成题",
    "练习题",
    "考试题",
    "测验题",
    "题目",
    "帮我出",
    "出几道",
    "出一些",
    "出一道",
    "出两道",
    "出三道",
    "出四道",
    "出五道",
    "选择题",
    "判断题",
    "填空题",
)

_SHORT_ANSWER_KEYWORDS = ("简答", "简答题", "填空", "简述")
_ESSAY_KEYWORDS = ("论述", "论述题", "分析题", "作文题")


def detect_question_type(message: str) -> str | None:
    """Detect requested question type from user message.

    Returns: "short_answer", "essay", or None (default = multiple choice).
    """
    for keyword in _ESSAY_KEYWORDS:
        if keyword in message:
            return "essay"
    for keyword in _SHORT_ANSWER_KEYWORDS:
        if keyword in message:
            return "short_answer"
    return None


def classify_intent(message: str) -> IntentType:
    """Classify user message intent: extract, generate, or chat.

    Rules:
    - Long text (>200 chars) likely contains educational content → extract
    - Contains question-generation keywords → generate
    - Everything else → chat (normal ReAct)
    """
    if len(message.strip()) >= _EXTRACT_MIN_LENGTH:
        return "extract"

    for keyword in _GENERATE_KEYWORDS:
        if keyword in message:
            return "generate"

    return "chat"
