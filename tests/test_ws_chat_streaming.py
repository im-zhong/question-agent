"""Tests for WS /ws/chat streaming via LangGraph."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessageChunk, ToolMessage
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


class TestWsChatStreaming:
    """Test the WebSocket streaming endpoint."""

    def test_sends_start_token_end(self) -> None:
        """WS receives start → token(s) → end protocol messages."""
        mock_graph = _make_mock_graph("你", "好", "！")

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

        assert messages[0]["type"] == "start"
        assert "conversation_id" in messages[0]
        assert messages[1] == {"type": "token", "content": "你"}
        assert messages[2] == {"type": "token", "content": "好"}
        assert messages[3] == {"type": "token", "content": "！"}
        assert messages[4] == {"type": "end"}

    def test_ignores_non_message_type(self) -> None:
        """WS ignores messages with type != 'message'."""
        mock_graph = _make_mock_graph("回复")

        with (
            patch("question_agent.main.create_chat_graph", new=AsyncMock(return_value=mock_graph)),
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
        assert messages[0]["type"] == "start"
        assert messages[-1] == {"type": "end"}

    def test_ignores_empty_content(self) -> None:
        """WS ignores messages with empty content."""
        mock_graph = _make_mock_graph("回复")

        with (
            patch("question_agent.main.create_chat_graph", new=AsyncMock(return_value=mock_graph)),
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
        """Each WS connection gets a unique thread_id when no conversation_id provided."""
        conversation_ids: list[str] = []

        mock_graph = _make_mock_graph("回复")

        with (
            patch("question_agent.main.create_chat_graph", new=AsyncMock(return_value=mock_graph)),
            TestClient(app) as client,
        ):
            # First connection
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"type": "message", "content": "你好1"})
                while True:
                    data = ws.receive_json()
                    if data["type"] == "start":
                        conversation_ids.append(data["conversation_id"])
                    if data["type"] == "end":
                        break

            # Second connection
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"type": "message", "content": "你好2"})
                while True:
                    data = ws.receive_json()
                    if data["type"] == "start":
                        conversation_ids.append(data["conversation_id"])
                    if data["type"] == "end":
                        break

        assert len(conversation_ids) == 2
        assert conversation_ids[0] != conversation_ids[1]

    def test_conversation_id_param_reuses_thread(self) -> None:
        """WS with conversation_id query param uses it as thread_id."""
        mock_graph = _make_mock_graph("回复")

        with (
            patch("question_agent.main.create_chat_graph", new=AsyncMock(return_value=mock_graph)),
            TestClient(app) as client,
        ):
            with client.websocket_connect("/ws/chat?conversation_id=test-conv-123") as ws:
                ws.send_json({"type": "message", "content": "你好"})
                while True:
                    data = ws.receive_json()
                    if data["type"] == "start":
                        assert data["conversation_id"] == "test-conv-123"
                    if data["type"] == "end":
                        break

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
            patch("question_agent.main.create_chat_graph", new=AsyncMock(return_value=mock_graph)),
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

    def test_sends_data_for_extract_tool_message(self) -> None:
        """WS sends type=data when a ToolMessage from extract_knowledge_points is received."""
        kp_content = json.dumps(
            [
                {
                    "name": "加速度",
                    "description": "速度变化率",
                    "tags": [{"value": "加速度", "category": "concept"}],
                }
            ]
        )

        async def mock_astream_with_tool(
            input_msg: dict[str, Any],
            config: dict[str, Any],
            stream_mode: str = "messages",
        ) -> Any:
            tool_msg = ToolMessage(
                content=kp_content,
                name="extract_knowledge_points",
                tool_call_id="forced_extract",
            )
            yield (tool_msg, {})
            yield (AIMessageChunk(content="已提取知识点"), {})

        mock_graph = MagicMock()
        mock_graph.astream = mock_astream_with_tool

        with (
            patch("question_agent.main.create_chat_graph", new=AsyncMock(return_value=mock_graph)),
            TestClient(app) as client,
        ):
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"type": "message", "content": "提取知识点"})
                messages = []
                while True:
                    data = ws.receive_json()
                    messages.append(data)
                    if data["type"] == "end":
                        break

        data_msgs = [m for m in messages if m["type"] == "data"]
        assert len(data_msgs) == 1
        assert data_msgs[0]["tool"] == "extract_knowledge_points"
        assert json.loads(data_msgs[0]["content"])[0]["name"] == "加速度"

    def test_sends_data_for_generate_tool_message(self) -> None:
        """WS sends type=data when a ToolMessage from generate_questions is received."""
        q_content = json.dumps(
            {
                "questions": [
                    {
                        "id": 1,
                        "stem_text": "什么是加速度？",
                        "options": [{"label": "A", "text": "速度变化率"}],
                        "correct_answer": "A",
                        "knowledge_point_name": "加速度",
                        "question_type": "definition",
                        "status": "success",
                    }
                ],
                "stats": {"total": 1, "successful": 1, "failed": 0},
            }
        )

        async def mock_astream_with_tool(
            input_msg: dict[str, Any],
            config: dict[str, Any],
            stream_mode: str = "messages",
        ) -> Any:
            tool_msg = ToolMessage(
                content=q_content,
                name="generate_questions",
                tool_call_id="forced_generate",
            )
            yield (tool_msg, {})
            yield (AIMessageChunk(content="已生成题目"), {})

        mock_graph = MagicMock()
        mock_graph.astream = mock_astream_with_tool

        with (
            patch("question_agent.main.create_chat_graph", new=AsyncMock(return_value=mock_graph)),
            TestClient(app) as client,
        ):
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"type": "message", "content": "出题"})
                messages = []
                while True:
                    data = ws.receive_json()
                    messages.append(data)
                    if data["type"] == "end":
                        break

        data_msgs = [m for m in messages if m["type"] == "data"]
        assert len(data_msgs) == 1
        assert data_msgs[0]["tool"] == "generate_questions"
        parsed = json.loads(data_msgs[0]["content"])
        assert parsed["questions"][0]["stem_text"] == "什么是加速度？"

    def test_ignores_unknown_tool_messages(self) -> None:
        """WS does not send data for ToolMessage from unknown tools."""

        async def mock_astream_with_unknown_tool(
            input_msg: dict[str, Any],
            config: dict[str, Any],
            stream_mode: str = "messages",
        ) -> Any:
            tool_msg = ToolMessage(
                content="some result",
                name="unknown_tool",
                tool_call_id="call_1",
            )
            yield (tool_msg, {})
            yield (AIMessageChunk(content="回复"), {})

        mock_graph = MagicMock()
        mock_graph.astream = mock_astream_with_unknown_tool

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

        data_msgs = [m for m in messages if m["type"] == "data"]
        assert len(data_msgs) == 0
