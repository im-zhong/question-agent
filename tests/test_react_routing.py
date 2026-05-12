"""Tests for ReAct conditional routing in question_agent.chat.graph.

Covers: _should_continue routing logic, graph structure with conditional edges,
and end-to-end tool-call routing through the compiled graph.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from question_agent.chat.graph import _should_continue, chat_node, create_chat_graph


class TestShouldContinue:
    """Tests for the _should_continue conditional edge function."""

    def test_returns_tools_when_tool_calls_present(self) -> None:
        """AIMessage with tool_calls routes to tools node."""
        tool_call = {"id": "tc1", "name": "extract_knowledge_points", "args": {"text": "hello"}}
        ai_msg = AIMessage(content="", tool_calls=[tool_call])
        state = {"messages": [HumanMessage(content="帮我出题"), ai_msg]}
        assert _should_continue(state) == "tools"

    def test_returns_end_when_no_tool_calls(self) -> None:
        """AIMessage without tool_calls routes to END."""
        ai_msg = AIMessage(content="你好！有什么可以帮你的吗？")
        state = {"messages": [HumanMessage(content="你好"), ai_msg]}
        assert _should_continue(state) == "__end__"

    def test_returns_end_when_last_message_is_human(self) -> None:
        """If last message is HumanMessage (non-standard), route to END."""
        state = {"messages": [HumanMessage(content="你好")]}
        assert _should_continue(state) == "__end__"

    def test_returns_end_when_empty_tool_calls_list(self) -> None:
        """AIMessage with empty tool_calls list routes to END."""
        ai_msg = AIMessage(content="好的", tool_calls=[])
        state = {"messages": [ai_msg]}
        assert _should_continue(state) == "__end__"

    def test_returns_tools_with_multiple_tool_calls(self) -> None:
        """AIMessage with multiple tool_calls routes to tools."""
        ai_msg = AIMessage(
            content="",
            tool_calls=[
                {"id": "tc1", "name": "extract_knowledge_points", "args": {"text": "text1"}},
                {
                    "id": "tc2",
                    "name": "generate_questions",
                    "args": {"knowledge_points_json": "[]"},
                },
            ],
        )
        state = {"messages": [HumanMessage(content="帮我出题"), ai_msg]}
        assert _should_continue(state) == "tools"

    def test_returns_end_with_tool_message_last(self) -> None:
        """ToolMessage as last message (shouldn't happen at conditional edge) routes to END."""
        tool_msg = ToolMessage(content="result", tool_call_id="tc1")
        state = {"messages": [tool_msg]}
        assert _should_continue(state) == "__end__"


class TestReActGraphStructure:
    """Tests for the compiled graph structure with ReAct routing."""

    def test_graph_has_tools_node(self) -> None:
        """Compiled graph contains a tools node."""
        graph = create_chat_graph()
        assert "tools" in graph.nodes

    def test_graph_has_chat_node(self) -> None:
        """Compiled graph contains a chat node."""
        graph = create_chat_graph()
        assert "chat" in graph.nodes

    def test_graph_compiles_successfully(self) -> None:
        """Graph with conditional edges compiles without error."""
        graph = create_chat_graph()
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "astream")

    def test_graph_multiple_compilations(self) -> None:
        """Multiple compilations produce valid graphs."""
        g1 = create_chat_graph()
        g2 = create_chat_graph()
        assert "chat" in g1.nodes and "tools" in g1.nodes
        assert "chat" in g2.nodes and "tools" in g2.nodes


class TestReActChatNodeWithTools:
    """Tests for chat_node with tools bound (ReAct pattern)."""

    @pytest.mark.asyncio
    async def test_chat_node_calls_llm_with_tools_bound(self) -> None:
        """chat_node uses LLM with tools bound for ReAct agent."""
        mock_response = AIMessage(content="让我来帮你出题", tool_calls=[])
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("question_agent.chat.graph._create_llm_with_tools", return_value=mock_llm):
            result = await chat_node({"messages": [HumanMessage(content="帮我出题")]})

        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)

    @pytest.mark.asyncio
    async def test_chat_node_returns_tool_call_response(self) -> None:
        """chat_node returns AIMessage with tool_calls for tool-routing."""
        tool_call = {
            "id": "tc1",
            "name": "extract_knowledge_points",
            "args": {"text": "物理学是研究物质运动的科学"},
        }
        mock_response = AIMessage(content="", tool_calls=[tool_call])
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("question_agent.chat.graph._create_llm_with_tools", return_value=mock_llm):
            result = await chat_node({"messages": [HumanMessage(content="帮我从这段文字出题")]})

        assert result["messages"][0].tool_calls is not None
        assert len(result["messages"][0].tool_calls) == 1
        assert result["messages"][0].tool_calls[0]["name"] == "extract_knowledge_points"
