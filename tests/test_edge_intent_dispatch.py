"""Edge cases for intent classification and dispatch node routing."""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from question_agent.chat.graph import dispatch_node
from question_agent.chat.intent import classify_intent, detect_question_type
from langgraph.graph import MessagesState


class TestIntentClassificationEdgeCases:
    """Edge cases for classify_intent."""

    def test_empty_string_is_chat(self) -> None:
        assert classify_intent("") == "chat"

    def test_whitespace_only_is_chat(self) -> None:
        assert classify_intent("   \t\n  ") == "chat"

    def test_emoji_only_is_chat(self) -> None:
        assert classify_intent("🎉🎉🎉") == "chat"

    def test_keyword_embedded_in_question_is_generate(self) -> None:
        """'出题' inside a question about the process still triggers generate."""
        assert classify_intent("我想了解出题流程") == "generate"

    def test_keyword_in_long_text_is_extract(self) -> None:
        """Long text with generate keyword should be extract (length priority)."""
        text = "出题" + "教材内容" * 60
        assert classify_intent(text) == "extract"

    def test_mixed_language_with_keyword(self) -> None:
        """Mixed CN/EN with generate keyword."""
        assert classify_intent("Please 帮我出题 for chapter 3") == "generate"

    def test_xuanzeti_variations(self) -> None:
        """Various expressions with 选择题."""
        assert classify_intent("来两道选择题") == "generate"
        assert classify_intent("选择题出5道") == "generate"

    def test_panduanti_is_generate(self) -> None:
        assert classify_intent("出3道判断题") == "generate"

    def test_tiankongti_is_generate(self) -> None:
        assert classify_intent("出两道填空题") == "generate"

    def test_chuang_zero_not_keyword(self) -> None:
        """出零道 is not a keyword — should be chat."""
        assert classify_intent("出零道") == "chat"

    def test_chuang_shidao_not_keyword(self) -> None:
        """出十道 is not in the keyword list — should be chat."""
        assert classify_intent("出十道题") == "chat"

    def test_generate_keyword_at_end(self) -> None:
        assert classify_intent("基于第三章的内容，出题") == "generate"

    def test_single_char_not_enough(self) -> None:
        """Just '题' alone is not a generate keyword."""
        assert classify_intent("题") == "chat"


class TestDetectQuestionTypeEdgeCases:
    """Edge cases for detect_question_type."""

    def test_no_keyword_returns_none(self) -> None:
        assert detect_question_type("出两道选择题") is None

    def test_jianda_keyword(self) -> None:
        assert detect_question_type("出两道简答题") == "short_answer"

    def test_lunshu_keyword(self) -> None:
        assert detect_question_type("出一道论述题") == "essay"

    def test_tiankong_keyword(self) -> None:
        assert detect_question_type("出三道填空题") == "short_answer"


class TestDispatchNodeEdgeCases:
    """Edge cases for dispatch_node."""

    @pytest.mark.asyncio
    async def test_kb_prefix_with_invalid_hex_still_parsed(self) -> None:
        """Invalid hex in kb prefix still gets parsed by regex."""
        # The regex matches [a-f0-9]+ so 'gg' won't match
        state: MessagesState = {
            "messages": [HumanMessage(content="[kb:gg] 出两道选择题")]
        }
        result = await dispatch_node(state)
        # 'gg' doesn't match [a-f0-9], so no kb_id extracted
        # Intent is generate (选择题 keyword), but no KB -> goes to generate without KB
        # Since no prior KPs in history, returns SystemMessage hint
        assert len(result["messages"]) == 1
        # It could be SystemMessage (no KPs) or AIMessage with tool_call
        # Since no KPs in history, it should be the SystemMessage hint

    @pytest.mark.asyncio
    async def test_generate_with_kb_and_chuang_liangdao(self) -> None:
        """The exact bug scenario: KB + 出两道选择题 should force fetch_kp."""
        state: MessagesState = {
            "messages": [HumanMessage(content="[kb:abc123] 基于语义计算工具库，出两道选择题")]
        }
        result = await dispatch_node(state)

        assert len(result["messages"]) == 1
        ai_msg = result["messages"][0]
        assert isinstance(ai_msg, AIMessage)
        assert ai_msg.tool_calls[0]["name"] == "fetch_knowledge_points_from_kb"
        assert ai_msg.tool_calls[0]["args"]["kb_id"] == "abc123"

    @pytest.mark.asyncio
    async def test_multiple_kb_prefixes_uses_first(self) -> None:
        """Only the first [kb:...] prefix is parsed."""
        state: MessagesState = {
            "messages": [
                HumanMessage(content="[kb:aaa111] [kb:bbb222] 出两道选择题")
            ]
        }
        result = await dispatch_node(state)
        ai_msg = result["messages"][0]
        assert isinstance(ai_msg, AIMessage)
        assert ai_msg.tool_calls[0]["args"]["kb_id"] == "aaa111"
