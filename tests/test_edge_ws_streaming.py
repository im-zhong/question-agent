"""Edge case tests for WS /ws/chat streaming — protocol and connection edge cases."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessageChunk
from starlette.testclient import TestClient

from question_agent.main import app


def _make_mock_graph(*chunks: str) -> MagicMock:
    """Create a mock graph that yields AIMessageChunks via astream."""

    async def mock_astream(
        input_msg: dict[str, Any],
        config: dict[str, Any] | None = None,
        stream_mode: str = "messages",
    ) -> Any:
        for chunk_text in chunks:
            yield (AIMessageChunk(content=chunk_text), {})

    graph = MagicMock()
    graph.astream = mock_astream
    graph.aget_state = AsyncMock(return_value=None)
    return graph


def _make_error_graph() -> MagicMock:
    """Create a mock graph that raises an exception during streaming."""

    async def mock_astream_error(
        input_msg: dict[str, Any],
        config: dict[str, Any] | None = None,
        stream_mode: str = "messages",
    ) -> Any:
        yield (AIMessageChunk(content="部分"), {})
        raise RuntimeError("LLM API error")

    graph = MagicMock()
    graph.astream = mock_astream_error
    return graph


class TestWsStreamingEdgeCases:
    """Edge cases for the WS streaming endpoint."""

    def test_unicode_emoji_content(self) -> None:
        """WS handles emoji and special unicode in AI responses."""
        mock_graph = _make_mock_graph("你好 🎉", "中日韓", "\U0001f600")

        with (
            patch("question_agent.main.create_chat_graph", new=AsyncMock(return_value=mock_graph)),
            TestClient(app) as client,
        ):
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"type": "message", "content": "emoji test"})
                messages = []
                while True:
                    data = ws.receive_json()
                    messages.append(data)
                    if data["type"] == "end":
                        break

        assert messages[1] == {"type": "token", "content": "你好 🎉"}
        assert messages[2] == {"type": "token", "content": "中日韓"}

    def test_very_long_single_token(self) -> None:
        """WS handles a very long single token (e.g., code block response)."""
        long_content = "代码" * 2000  # 4k chars
        mock_graph = _make_mock_graph(long_content)

        with (
            patch("question_agent.main.create_chat_graph", new=AsyncMock(return_value=mock_graph)),
            TestClient(app) as client,
        ):
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"type": "message", "content": "show me code"})
                messages = []
                while True:
                    data = ws.receive_json()
                    messages.append(data)
                    if data["type"] == "end":
                        break

        assert len(messages) == 3  # start + 1 token + end
        assert len(messages[1]["content"]) == 4000

    def test_message_without_type_field(self) -> None:
        """WS ignores messages missing the 'type' field."""
        mock_graph = _make_mock_graph("回复")

        with (
            patch("question_agent.main.create_chat_graph", new=AsyncMock(return_value=mock_graph)),
            TestClient(app) as client,
        ):
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"content": "no type field"})
                ws.send_json({"type": "message", "content": "with type"})
                messages = []
                while True:
                    data = ws.receive_json()
                    messages.append(data)
                    if data["type"] == "end":
                        break

        # Only one response for the message with correct type
        start_count = sum(1 for m in messages if m["type"] == "start")
        assert start_count == 1

    def test_message_without_content_field(self) -> None:
        """WS ignores messages missing the 'content' field (treated as empty)."""
        mock_graph = _make_mock_graph("回复")

        with (
            patch("question_agent.main.create_chat_graph", new=AsyncMock(return_value=mock_graph)),
            TestClient(app) as client,
        ):
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"type": "message"})
                ws.send_json({"type": "message", "content": "has content"})
                messages = []
                while True:
                    data = ws.receive_json()
                    messages.append(data)
                    if data["type"] == "end":
                        break

        start_count = sum(1 for m in messages if m["type"] == "start")
        assert start_count == 1

    def test_multiple_rapid_messages(self) -> None:
        """WS handles multiple rapid messages in sequence."""
        call_count = 0

        async def mock_astream_count(
            input_msg: dict[str, Any],
            config: dict[str, Any] | None = None,
            stream_mode: str = "messages",
        ) -> Any:
            nonlocal call_count
            call_count += 1
            yield (AIMessageChunk(content=f"r{call_count}"), {})

        mock_graph = MagicMock()
        mock_graph.astream = mock_astream_count

        with (
            patch("question_agent.main.create_chat_graph", new=AsyncMock(return_value=mock_graph)),
            TestClient(app) as client,
        ):
            with client.websocket_connect("/ws/chat") as ws:
                for i in range(5):
                    ws.send_json({"type": "message", "content": f"msg{i}"})
                    # Must consume all response events before sending next
                    while True:
                        data = ws.receive_json()
                        if data["type"] == "end":
                            break

        assert call_count == 5

    def test_graph_streaming_error_sends_error_and_end(self) -> None:
        """WS sends partial tokens, then error event, then end when LLM fails."""
        mock_graph = _make_error_graph()

        with (
            patch("question_agent.main.create_chat_graph", new=AsyncMock(return_value=mock_graph)),
            TestClient(app) as client,
        ):
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"type": "message", "content": "trigger error"})
                messages = []
                while True:
                    data = ws.receive_json()
                    messages.append(data)
                    if data["type"] == "end":
                        break

        assert messages[0]["type"] == "start"
        assert messages[1]["type"] == "token"
        assert messages[1]["content"] == "部分"
        assert messages[2]["type"] == "error"
        assert messages[3]["type"] == "end"
