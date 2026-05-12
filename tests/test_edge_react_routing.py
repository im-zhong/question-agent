"""Edge case tests for ReAct conditional routing.

Covers: empty state, single message, tool_calls with invalid structure,
non-AIMessage last message types, and graph-level routing edge cases.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)

from question_agent.chat.graph import _should_continue, chat_node


class TestShouldContinueEdgeCases:
    """Edge cases for the _should_continue conditional edge function."""

    def test_system_message_as_last_message(self) -> None:
        """SystemMessage as last message routes to END (non-AIMessage)."""
        state = {"messages": [SystemMessage(content="You are a helpful assistant")]}
        assert _should_continue(state) == "__end__"

    def test_remove_message_as_last_message(self) -> None:
        """RemoveMessage as last message routes to END (non-AIMessage)."""
        state = {"messages": [RemoveMessage(id="msg1")]}
        assert _should_continue(state) == "__end__"

    def test_ai_message_with_none_tool_calls(self) -> None:
        """AIMessage with tool_calls=None routes to END."""
        ai_msg = AIMessage(content="直接回复")
        assert ai_msg.tool_calls is None or ai_msg.tool_calls == []
        state = {"messages": [ai_msg]}
        assert _should_continue(state) == "__end__"

    def test_long_conversation_history_routes_correctly(self) -> None:
        """Long conversation with tool_calls in last AI message routes to tools."""
        history: list = [HumanMessage(content="问题1")]
        for i in range(10):
            history.append(AIMessage(content=f"回答{i}"))
            history.append(HumanMessage(content=f"问题{i + 2}"))
        # Last AI message with tool_calls
        tool_call = {"id": "tc1", "name": "extract_knowledge_points", "args": {"text": "test"}}
        history.append(AIMessage(content="", tool_calls=[tool_call]))
        state = {"messages": history}
        assert _should_continue(state) == "tools"

    def test_tool_call_with_empty_args(self) -> None:
        """Tool call with empty args dict still routes to tools."""
        ai_msg = AIMessage(content="", tool_calls=[{"id": "tc1", "name": "some_tool", "args": {}}])
        state = {"messages": [ai_msg]}
        assert _should_continue(state) == "tools"


class TestReActChatNodeEdgeCases:
    """Edge cases for chat_node in ReAct mode."""

    @pytest.mark.asyncio
    async def test_chat_node_with_system_and_human_messages(self) -> None:
        """chat_node handles system + human messages correctly."""
        mock_response = AIMessage(content="理解了，我来帮你出题")
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        messages = [
            SystemMessage(content="你是一个出题助手"),
            HumanMessage(content="帮我出题"),
        ]

        with patch("question_agent.chat.graph._create_llm_with_tools", return_value=mock_llm):
            result = await chat_node({"messages": messages})

        assert len(result["messages"]) == 1
        # Verify LLM received all messages including system message
        call_args = mock_llm.ainvoke.call_args[0][0]
        assert len(call_args) == 2

    @pytest.mark.asyncio
    async def test_chat_node_with_prior_tool_messages(self) -> None:
        """chat_node handles state with prior ToolMessage results (after tool execution)."""
        mock_response = AIMessage(content="根据知识点，我为你生成了以下题目...")
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        messages = [
            HumanMessage(content="帮我出题"),
            AIMessage(
                content="",
                tool_calls=[
                    {"id": "tc1", "name": "extract_knowledge_points", "args": {"text": "test"}}
                ],
            ),
            ToolMessage(content='[{"name": "知识点1"}]', tool_call_id="tc1"),
        ]

        with patch("question_agent.chat.graph._create_llm_with_tools", return_value=mock_llm):
            result = await chat_node({"messages": messages})

        assert len(result["messages"]) == 1
        # Verify LLM received the full history including tool results
        call_args = mock_llm.ainvoke.call_args[0][0]
        assert len(call_args) == 3
