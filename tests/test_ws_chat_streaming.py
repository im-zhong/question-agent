"""Tests for WS /ws/chat streaming via LangGraph."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessageChunk
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
    return graph


class TestWsChatStreaming:
    """Test the WebSocket streaming endpoint."""

    def test_sends_start_token_end(self) -> None:
        """WS receives start → token(s) → end protocol messages."""
        mock_graph = _make_mock_graph("你", "好", "！")

        with (
            patch("question_agent.main.create_chat_graph", return_value=mock_graph),
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

        assert messages[0] == {"type": "start"}
        assert messages[1] == {"type": "token", "content": "你"}
        assert messages[2] == {"type": "token", "content": "好"}
        assert messages[3] == {"type": "token", "content": "！"}
        assert messages[4] == {"type": "end"}

    def test_ignores_non_message_type(self) -> None:
        """WS ignores messages with type != 'message'."""
        mock_graph = _make_mock_graph("回复")

        with (
            patch("question_agent.main.create_chat_graph", return_value=mock_graph),
            TestClient(app) as client,
        ):
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"type": "ping", "content": "hello"})
                # Send a real message to verify the handler is still alive
                ws.send_json({"type": "message", "content": "你好"})
                messages = []
                while True:
                    data = ws.receive_json()
                    messages.append(data)
                    if data["type"] == "end":
                        break

        # Should only get response for the second message
        assert messages[0] == {"type": "start"}
        assert messages[-1] == {"type": "end"}

    def test_ignores_empty_content(self) -> None:
        """WS ignores messages with empty content."""
        mock_graph = _make_mock_graph("回复")

        with (
            patch("question_agent.main.create_chat_graph", return_value=mock_graph),
            TestClient(app) as client,
        ):
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"type": "message", "content": ""})
                ws.send_json({"type": "message", "content": "你好"})
                messages = []
                while True:
                    data = ws.receive_json()
                    messages.append(data)
                    if data["type"] == "end":
                        break

        # Only one response (for the non-empty message)
        start_count = sum(1 for m in messages if m["type"] == "start")
        end_count = sum(1 for m in messages if m["type"] == "end")
        assert start_count == 1
        assert end_count == 1

    def test_unique_thread_id_per_connection(self) -> None:
        """Each WS connection gets a unique thread_id."""
        thread_ids: list[str] = []

        original_uuid4 = uuid.uuid4

        def mock_uuid4() -> uuid.UUID:
            uid = original_uuid4()
            thread_ids.append(str(uid))
            return uid

        mock_graph = _make_mock_graph("回复")

        with (
            patch("question_agent.main.create_chat_graph", return_value=mock_graph),
            patch("question_agent.main.uuid.uuid4", side_effect=mock_uuid4),
            TestClient(app) as client,
        ):
            # First connection
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"type": "message", "content": "你好1"})
                while True:
                    data = ws.receive_json()
                    if data["type"] == "end":
                        break

            # Second connection
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"type": "message", "content": "你好2"})
                while True:
                    data = ws.receive_json()
                    if data["type"] == "end":
                        break

        assert len(thread_ids) == 2
        assert thread_ids[0] != thread_ids[1]

    def test_multiple_messages_in_same_session(self) -> None:
        """Multiple messages in one WS connection use the same graph (thread continuity)."""
        call_count = 0

        async def mock_astream_count(
            input_msg: dict[str, Any],
            config: dict[str, Any],
            stream_mode: str = "messages",
        ) -> Any:
            nonlocal call_count
            call_count += 1
            yield (AIMessageChunk(content=f"回复{call_count}"), {})

        mock_graph = MagicMock()
        mock_graph.astream = mock_astream_count

        with (
            patch("question_agent.main.create_chat_graph", return_value=mock_graph),
            TestClient(app) as client,
        ):
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"type": "message", "content": "问题1"})
                while True:
                    data = ws.receive_json()
                    if data["type"] == "end":
                        break

                ws.send_json({"type": "message", "content": "问题2"})
                while True:
                    data = ws.receive_json()
                    if data["type"] == "end":
                        break

        assert call_count == 2
