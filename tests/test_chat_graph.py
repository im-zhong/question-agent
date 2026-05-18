"""Unit tests for question_agent.chat module."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from question_agent.chat import graph as chat_graph
from question_agent.chat.graph import chat_node, create_chat_graph, get_checkpointer

_TEST_DB = Path("/tmp/test_chat_graph.db")


@pytest.fixture(autouse=True)
def _reset_checkpointer() -> None:
    """Reset the checkpointer singleton between tests."""
    chat_graph._checkpointer = None


@pytest.mark.asyncio
async def test_create_chat_graph_returns_compiled() -> None:
    """create_chat_graph returns a compiled graph with chat node."""
    with patch.object(chat_graph.settings, "chat_db_path", _TEST_DB):
        graph = await create_chat_graph()
    assert "chat" in graph.nodes


@pytest.mark.asyncio
async def test_get_checkpointer_returns_singleton() -> None:
    """get_checkpointer returns the same AsyncSqliteSaver instance."""
    with patch.object(chat_graph.settings, "chat_db_path", _TEST_DB):
        cp1 = await get_checkpointer()
        cp2 = await get_checkpointer()
    assert cp1 is cp2
    assert isinstance(cp1, AsyncSqliteSaver)


@pytest.mark.asyncio
async def test_chat_node_returns_ai_message() -> None:
    """chat_node invokes LLM and returns AIMessage in messages list."""
    mock_response = AIMessage(content="你好！有什么可以帮你的吗？")
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("question_agent.chat.graph._create_llm_with_tools", return_value=mock_llm):
        result = await chat_node({"messages": [HumanMessage(content="你好")]})

    assert "messages" in result
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], AIMessage)
    assert result["messages"][0].content == "你好！有什么可以帮你的吗？"


@pytest.mark.asyncio
async def test_chat_node_accumulates_history() -> None:
    """chat_node receives full conversation history and appends response."""
    mock_response = AIMessage(content="是的，我可以帮助你。")
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    history = [
        HumanMessage(content="你好"),
        AIMessage(content="你好！"),
        HumanMessage(content="你能帮我吗？"),
    ]

    with patch("question_agent.chat.graph._create_llm_with_tools", return_value=mock_llm):
        result = await chat_node({"messages": history})

    # Verify LLM received the full history
    call_args = mock_llm.ainvoke.call_args[0][0]
    assert len(call_args) == 3
    assert result["messages"][0].content == "是的，我可以帮助你。"
