"""Unit tests for question_agent.chat module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from question_agent.chat.graph import chat_node, create_chat_graph, get_checkpointer


def test_create_chat_graph_returns_compiled() -> None:
    """create_chat_graph returns a compiled graph with chat node."""
    graph = create_chat_graph()
    assert "chat" in graph.nodes


def test_get_checkpointer_returns_singleton() -> None:
    """get_checkpointer returns the same MemorySaver instance."""
    cp1 = get_checkpointer()
    cp2 = get_checkpointer()
    assert cp1 is cp2


@pytest.mark.asyncio
async def test_chat_node_returns_ai_message() -> None:
    """chat_node invokes LLM and returns AIMessage in messages list."""
    mock_response = AIMessage(content="你好！有什么可以帮你的吗？")
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("question_agent.chat.graph._create_llm", return_value=mock_llm):
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

    with patch("question_agent.chat.graph._create_llm", return_value=mock_llm):
        result = await chat_node({"messages": history})

    # Verify LLM received the full history
    call_args = mock_llm.ainvoke.call_args[0][0]
    assert len(call_args) == 3
    assert result["messages"][0].content == "是的，我可以帮助你。"
