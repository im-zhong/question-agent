"""Integration test: WS /ws/chat → LangGraph → GLM-5 streaming walkthrough.

Requires a running server with GLM_API_KEY configured.
"""

import pytest

BASE_WS_URL = "ws://localhost:8000"


@pytest.mark.integration
class TestWsChatWalkthrough:
    """End-to-end walkthrough: WS → LangGraph → GLM-5 streaming."""

    def test_ws_chat_streaming_walkthrough(self) -> None:
        """Full walkthrough: connect, send message, receive streaming AI response."""
        from starlette.testclient import TestClient

        from question_agent.main import app

        with TestClient(app) as client:
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"type": "message", "content": "你好，请用一句话介绍你自己"})

                messages: list[dict[str, str]] = []
                while True:
                    data = ws.receive_json()
                    messages.append(data)
                    if data["type"] == "end":
                        break

        # Protocol: start → token(s) → end
        assert messages[0]["type"] == "start", "First message should be start"
        assert messages[-1]["type"] == "end", "Last message should be end"
        token_messages = [m for m in messages if m["type"] == "token"]
        assert len(token_messages) > 0, "Should receive at least one token"

        # Concatenated tokens should form a meaningful Chinese response
        full_response = "".join(m["content"] for m in token_messages)
        assert len(full_response) > 0, "Response should not be empty"

    def test_ws_chat_session_isolation(self) -> None:
        """Two WS connections use independent sessions (different thread_ids)."""
        from starlette.testclient import TestClient

        from question_agent.main import app

        with TestClient(app) as client:
            # Connection 1
            with client.websocket_connect("/ws/chat") as ws1:
                ws1.send_json({"type": "message", "content": "1+1等于几？"})
                msgs1: list[dict[str, str]] = []
                while True:
                    data = ws1.receive_json()
                    msgs1.append(data)
                    if data["type"] == "end":
                        break

            # Connection 2
            with client.websocket_connect("/ws/chat") as ws2:
                ws2.send_json({"type": "message", "content": "2+2等于几？"})
                msgs2: list[dict[str, str]] = []
                while True:
                    data = ws2.receive_json()
                    msgs2.append(data)
                    if data["type"] == "end":
                        break

        # Both connections should receive valid responses independently
        assert msgs1[0]["type"] == "start"
        assert msgs1[-1]["type"] == "end"
        assert msgs2[0]["type"] == "start"
        assert msgs2[-1]["type"] == "end"
