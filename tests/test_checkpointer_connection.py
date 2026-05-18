"""Tests for AsyncSqliteSaver connection lifecycle.

Reproduces: ValueError "no active connection" when using
AsyncSqliteSaver.from_conn_string().__aenter__() — the context manager
gets garbage-collected, closing the underlying aiosqlite connection.
Fix: use aiosqlite.connect() directly and pass the conn to AsyncSqliteSaver.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, MessagesState, StateGraph

from question_agent.chat import graph as chat_graph

_TEST_DB = Path("/tmp/test_checkpointer_connection.db")


@pytest.fixture(autouse=True)
def _reset_checkpointer() -> None:
    """Reset the checkpointer singleton between tests."""
    chat_graph._checkpointer = None
    chat_graph._db_conn = None


class TestCheckpointerConnectionStaysAlive:
    """Verify that the AsyncSqliteSaver connection is not prematurely closed."""

    @pytest.mark.asyncio
    async def test_aget_state_after_get_checkpointer(self) -> None:
        """get_checkpointer() returns a checkpointer with an active connection.

        Calling aget_state on a graph using that checkpointer should not
        raise ValueError("no active connection").
        """
        with patch.object(chat_graph.settings, "chat_db_path", _TEST_DB):
            cp = await chat_graph.get_checkpointer()

        # Build a minimal graph with the checkpointer
        async def echo_node(state: MessagesState) -> dict:
            return {"messages": state["messages"]}

        g = StateGraph(MessagesState)
        g.add_node("echo", echo_node)
        g.add_edge(START, "echo")
        g.add_edge("echo", END)
        compiled = g.compile(checkpointer=cp)

        config = {"configurable": {"thread_id": "conn-test"}}
        # This should NOT raise ValueError("no active connection")
        state = await compiled.aget_state(config)
        assert state is not None

    @pytest.mark.asyncio
    async def test_astream_after_get_checkpointer(self) -> None:
        """Streaming through a graph with the checkpointer keeps the connection alive."""
        with patch.object(chat_graph.settings, "chat_db_path", _TEST_DB):
            cp = await chat_graph.get_checkpointer()

        async def echo_node(state: MessagesState) -> dict:
            return {"messages": state["messages"]}

        g = StateGraph(MessagesState)
        g.add_node("echo", echo_node)
        g.add_edge(START, "echo")
        g.add_edge("echo", END)
        compiled = g.compile(checkpointer=cp)

        config = {"configurable": {"thread_id": "stream-test"}}
        input_msg = {"messages": [HumanMessage(content="hello")]}

        # Use stream_mode="values" — echo_node returns the same messages,
        # so "messages" mode yields no new chunks but "values" mode does.
        chunks = []
        async for chunk in compiled.astream(input_msg, config=config, stream_mode="values"):
            chunks.append(chunk)

        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_aget_state_via_create_chat_graph(self) -> None:
        """The full chat graph's checkpointer also has an active connection."""
        with patch.object(chat_graph.settings, "chat_db_path", _TEST_DB):
            compiled = await chat_graph.create_chat_graph()

        config = {"configurable": {"thread_id": "full-graph-test"}}
        state = await compiled.aget_state(config)
        assert state is not None
