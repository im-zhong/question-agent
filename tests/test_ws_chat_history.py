"""Tests for WS /ws/chat conversation history replay."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from starlette.testclient import TestClient

from question_agent.main import app


def _make_mock_graph(*chunks: str) -> MagicMock:
    """Create a mock graph that yields AIMessageChunks via astream."""

    async def mock_astream(
        input_msg: dict[str, Any],
        config: dict[str, Any],
        stream_mode: str = "messages",
    ) -> Any:
        for chunk_text in chunks:
            yield (AIMessageChunk(content=chunk_text), {})

    graph = MagicMock()
    graph.astream = mock_astream
    graph.aget_state = AsyncMock(return_value=None)
    return graph


class TestWsChatHistory:
    """Test conversation history replay on reconnection."""

    def test_no_history_for_new_conversation(self) -> None:
        """New conversation (no conversation_id) does not receive history."""
        mock_graph = _make_mock_graph("回复")

        with (
            patch("question_agent.main.create_chat_graph", new=AsyncMock(return_value=mock_graph)),
            TestClient(app) as client,
        ):
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"type": "message", "content": "你好"})
                messages = []
                while True:
                    data = ws.receive_json()
                    messages.append(data)
                    if data["type"] == "end":
                        break

        # No history message, only start + tokens + end
        assert not any(m["type"] == "history" for m in messages)

    def test_history_replay_for_existing_conversation(self) -> None:
        """Reconnecting with conversation_id replays stored messages."""
        checkpoint_state = MagicMock()
        checkpoint_state.values = {
            "messages": [
                HumanMessage(content="问题1"),
                AIMessage(content="回答1"),
                HumanMessage(content="问题2"),
                AIMessage(content="回答2"),
            ]
        }

        mock_graph = _make_mock_graph("新回复")
        mock_graph.aget_state = AsyncMock(return_value=checkpoint_state)

        with (
            patch("question_agent.main.create_chat_graph", new=AsyncMock(return_value=mock_graph)),
            TestClient(app) as client,
        ):
            with client.websocket_connect("/ws/chat?conversation_id=conv-123") as ws:
                # First message should be history
                history_msg = ws.receive_json()
                assert history_msg["type"] == "history"
                assert len(history_msg["messages"]) == 4
                assert history_msg["messages"][0] == {"role": "user", "content": "问题1"}
                assert history_msg["messages"][1] == {"role": "ai", "content": "回答1"}

                # Then normal interaction
                ws.send_json({"type": "message", "content": "继续"})
                while True:
                    data = ws.receive_json()
                    if data["type"] == "end":
                        break

    def test_empty_history_no_history_message(self) -> None:
        """Existing conversation with empty state does not send history message."""
        checkpoint_state = MagicMock()
        checkpoint_state.values = {"messages": []}

        mock_graph = _make_mock_graph("回复")
        mock_graph.aget_state = AsyncMock(return_value=checkpoint_state)

        with (
            patch("question_agent.main.create_chat_graph", new=AsyncMock(return_value=mock_graph)),
            TestClient(app) as client,
        ):
            with client.websocket_connect("/ws/chat?conversation_id=conv-empty") as ws:
                ws.send_json({"type": "message", "content": "你好"})
                messages = []
                while True:
                    data = ws.receive_json()
                    messages.append(data)
                    if data["type"] == "end":
                        break

        assert not any(m["type"] == "history" for m in messages)

    def test_no_checkpoint_no_history_message(self) -> None:
        """Conversation with no checkpoint state does not send history message."""
        mock_graph = _make_mock_graph("回复")
        mock_graph.aget_state = AsyncMock(return_value=None)

        with (
            patch("question_agent.main.create_chat_graph", new=AsyncMock(return_value=mock_graph)),
            TestClient(app) as client,
        ):
            with client.websocket_connect("/ws/chat?conversation_id=conv-none") as ws:
                ws.send_json({"type": "message", "content": "你好"})
                messages = []
                while True:
                    data = ws.receive_json()
                    messages.append(data)
                    if data["type"] == "end":
                        break

        assert not any(m["type"] == "history" for m in messages)
