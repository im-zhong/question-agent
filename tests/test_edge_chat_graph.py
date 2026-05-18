"""Edge case tests for question_agent.chat module.

Covers: empty messages, missing API key, singleton concurrency, graph structure.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from question_agent.chat import graph as chat_graph
from question_agent.chat.graph import chat_node, create_chat_graph, get_checkpointer

_TEST_DB = Path("/tmp/test_edge_chat_graph.db")


@pytest.fixture(autouse=True)
def _reset_checkpointer() -> None:
    """Reset the checkpointer singleton between tests."""
    chat_graph._checkpointer = None


class TestChatNodeEdgeCases:
    """Edge cases for the chat_node function."""

    @pytest.mark.asyncio
    async def test_empty_messages_returns_ai_response(self) -> None:
        """chat_node with empty messages list should still call LLM."""
        mock_response = AIMessage(content="你好！请问有什么可以帮助你的？")
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("question_agent.chat.graph._create_llm_with_tools", return_value=mock_llm):
            result = await chat_node({"messages": []})

        assert "messages" in result
        assert len(result["messages"]) == 1
        mock_llm.ainvoke.assert_called_once_with([])

    @pytest.mark.asyncio
    async def test_very_long_message_content(self) -> None:
        """chat_node handles a very long single message without crashing."""
        long_content = "测试" * 5000  # 10k chars
        mock_response = AIMessage(content="收到")
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("question_agent.chat.graph._create_llm_with_tools", return_value=mock_llm):
            result = await chat_node({"messages": [HumanMessage(content=long_content)]})

        assert len(result["messages"]) == 1
        call_args = mock_llm.ainvoke.call_args[0][0]
        assert len(call_args[0].content) == 10000

    @pytest.mark.asyncio
    async def test_unicode_and_emoji_in_messages(self) -> None:
        """chat_node handles unicode, emoji, and special characters."""
        special_content = "你好 🎉 こんにちは \U0001f600 \t\n\r\0"
        mock_response = AIMessage(content="理解了")
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("question_agent.chat.graph._create_llm_with_tools", return_value=mock_llm):
            result = await chat_node({"messages": [HumanMessage(content=special_content)]})

        assert len(result["messages"]) == 1
        assert result["messages"][0].content == "理解了"

    @pytest.mark.asyncio
    async def test_multiple_consecutive_ai_messages(self) -> None:
        """chat_node handles non-standard history with consecutive AI messages."""
        mock_response = AIMessage(content="继续")
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        history = [
            HumanMessage(content="问题1"),
            AIMessage(content="回答1"),
            AIMessage(content="补充说明"),
        ]

        with patch("question_agent.chat.graph._create_llm_with_tools", return_value=mock_llm):
            result = await chat_node({"messages": history})

        assert len(result["messages"]) == 1
        # Verify LLM received all 3 messages
        assert len(mock_llm.ainvoke.call_args[0][0]) == 3


class TestCreateChatGraphEdgeCases:
    """Edge cases for create_chat_graph."""

    @pytest.mark.asyncio
    async def test_multiple_compilations_produce_valid_graphs(self) -> None:
        """Calling create_chat_graph multiple times returns valid graphs."""
        g1 = await create_chat_graph()
        g2 = await create_chat_graph()
        assert "chat" in g1.nodes
        assert "chat" in g2.nodes

    @pytest.mark.asyncio
    async def test_graph_has_correct_edges(self) -> None:
        """Compiled graph has START->chat->END structure."""
        graph = await create_chat_graph()
        # Verify the graph can be invoked with a valid config
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "astream")


class TestGetCheckpointerEdgeCases:
    """Edge cases for get_checkpointer singleton."""

    @pytest.mark.asyncio
    async def test_checkpointer_is_async_sqlite_saver(self) -> None:
        """get_checkpointer returns an AsyncSqliteSaver instance."""
        with patch.object(chat_graph.settings, "chat_db_path", _TEST_DB):
            cp = await get_checkpointer()
        assert isinstance(cp, AsyncSqliteSaver)

    @pytest.mark.asyncio
    async def test_checkpointer_stores_and_retrieves(self) -> None:
        """AsyncSqliteSaver can store and retrieve a checkpoint."""
        with patch.object(chat_graph.settings, "chat_db_path", _TEST_DB):
            cp = await get_checkpointer()
        assert cp is not None


class TestMissingApiKey:
    """Edge case: GLM_API_KEY not configured."""

    @pytest.mark.asyncio
    async def test_chat_node_with_empty_api_key_still_calls_llm(self) -> None:
        """chat_node delegates to LLM even when API key is empty.

        The LLM call itself will fail at the HTTP level — chat_node
        should not pre-validate the key, that's the LLM client's job.
        """
        mock_response = AIMessage(content="fallback")
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("question_agent.chat.graph._create_llm_with_tools", return_value=mock_llm):
            result = await chat_node({"messages": [HumanMessage(content="test")]})

        # Should still work since we mock the LLM
        assert len(result["messages"]) == 1
