"""Tests for intent classification and dispatch node routing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import MessagesState

from question_agent.chat import graph as chat_graph
from question_agent.chat.graph import (
    _extract_kp_from_history,
    _route_after_dispatch,
    create_chat_graph,
    dispatch_node,
)
from question_agent.chat.intent import classify_intent

_TEST_DB = Path("/tmp/test_dispatch_graph.db")


@pytest.fixture(autouse=True)
def _reset_checkpointer() -> None:
    """Reset the checkpointer singleton between tests."""
    chat_graph._checkpointer = None


# --- Intent classification tests ---


class TestClassifyIntent:
    def test_long_text_is_extract(self) -> None:
        """Long text (>200 chars) classified as extract."""
        text = "这是一段很长的教材内容" * 20  # >200 chars
        assert classify_intent(text) == "extract"

    def test_generate_keyword_triggers_generate(self) -> None:
        """Messages containing generate keywords classified as generate."""
        assert classify_intent("帮我出题") == "generate"
        assert classify_intent("生成练习题") == "generate"
        assert classify_intent("出几道考试题") == "generate"

    def test_short_non_keyword_is_chat(self) -> None:
        """Short messages without keywords classified as chat."""
        assert classify_intent("你好") == "chat"
        assert classify_intent("什么是知识点？") == "chat"
        assert classify_intent("") == "chat"

    def test_short_text_with_keyword_is_generate(self) -> None:
        """Short text with generate keyword takes priority over chat."""
        assert classify_intent("帮我出题") == "generate"

    def test_chuang_liangdao_is_generate(self) -> None:
        """出两道选择题 should be classified as generate, not chat."""
        assert classify_intent("基于语义计算工具库，出两道选择题") == "generate"

    def test_chuang_yidao_is_generate(self) -> None:
        """出一道题 should be classified as generate."""
        assert classify_intent("出一道题") == "generate"

    def test_chuang_sandao_is_generate(self) -> None:
        """出三道题 should be classified as generate."""
        assert classify_intent("出三道题") == "generate"

    def test_xuanzeti_is_generate(self) -> None:
        """选择题 keyword should be classified as generate."""
        assert classify_intent("出两道选择题") == "generate"


# --- Dispatch node tests ---


class TestDispatchNode:
    @pytest.mark.asyncio
    async def test_chat_intent_returns_empty(self) -> None:
        """Chat intent: dispatch returns no extra messages."""
        state: MessagesState = {"messages": [HumanMessage(content="你好")]}
        result = await dispatch_node(state)
        assert result["messages"] == []

    @pytest.mark.asyncio
    async def test_extract_intent_returns_forced_tool_call(self) -> None:
        """Extract intent: dispatch creates synthetic AIMessage with tool_call."""
        long_text = "教材内容" * 60
        state: MessagesState = {"messages": [HumanMessage(content=long_text)]}
        result = await dispatch_node(state)

        assert len(result["messages"]) == 1
        ai_msg = result["messages"][0]
        assert isinstance(ai_msg, AIMessage)
        assert len(ai_msg.tool_calls) == 1
        assert ai_msg.tool_calls[0]["name"] == "extract_knowledge_points"
        assert "text" in ai_msg.tool_calls[0]["args"]

    @pytest.mark.asyncio
    async def test_generate_intent_with_existing_kp(self) -> None:
        """Generate intent with KPs in history: dispatch forces generate_questions."""
        kp_json = '[{"name":"知识点1","description":"描述","tags":[]}]'
        extract_tc = {
            "name": "extract_knowledge_points",
            "args": {},
            "id": "t1",
            "type": "tool_call",
        }
        state: MessagesState = {
            "messages": [
                HumanMessage(content="长教材内容" * 60),
                AIMessage(content="", tool_calls=[extract_tc]),
                ToolMessage(content=kp_json, name="extract_knowledge_points", tool_call_id="t1"),
                HumanMessage(content="帮我出题"),
            ]
        }
        result = await dispatch_node(state)

        assert len(result["messages"]) == 1
        ai_msg = result["messages"][0]
        assert isinstance(ai_msg, AIMessage)
        assert len(ai_msg.tool_calls) == 1
        assert ai_msg.tool_calls[0]["name"] == "generate_questions"

    @pytest.mark.asyncio
    async def test_generate_intent_without_kp_returns_hint(self) -> None:
        """Generate intent without KPs: dispatch returns system hint."""
        state: MessagesState = {"messages": [HumanMessage(content="帮我出题")]}
        result = await dispatch_node(state)

        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], SystemMessage)

    @pytest.mark.asyncio
    async def test_generate_intent_with_kb_prefix_forces_fetch(self) -> None:
        """Generate intent + KB prefix: dispatch forces fetch_knowledge_points_from_kb."""
        state: MessagesState = {"messages": [HumanMessage(content="[kb:abc123] 出两道选择题")]}
        result = await dispatch_node(state)

        assert len(result["messages"]) == 1
        ai_msg = result["messages"][0]
        assert isinstance(ai_msg, AIMessage)
        assert len(ai_msg.tool_calls) == 1
        assert ai_msg.tool_calls[0]["name"] == "fetch_knowledge_points_from_kb"
        assert ai_msg.tool_calls[0]["args"]["kb_id"] == "abc123"

    @pytest.mark.asyncio
    async def test_no_user_message_returns_empty(self) -> None:
        """No user message in state: dispatch returns empty."""
        state: MessagesState = {"messages": [AIMessage(content="你好")]}
        result = await dispatch_node(state)
        assert result["messages"] == []


# --- Route after dispatch tests ---


class TestRouteAfterDispatch:
    def test_routes_to_tools_for_forced_call(self) -> None:
        """When dispatch added AIMessage with tool_calls, route to tools."""
        extract_tc = {
            "name": "extract_knowledge_points",
            "args": {},
            "id": "f1",
            "type": "tool_call",
        }
        state: MessagesState = {
            "messages": [
                HumanMessage(content="教材" * 60),
                AIMessage(content="", tool_calls=[extract_tc]),
            ]
        }
        assert _route_after_dispatch(state) == "tools"

    def test_routes_to_chat_for_no_tool_call(self) -> None:
        """When dispatch added no tool_calls, route to chat."""
        state: MessagesState = {"messages": [HumanMessage(content="你好")]}
        assert _route_after_dispatch(state) == "chat"


# --- _extract_kp_from_history tests ---


class TestExtractKpFromHistory:
    def test_finds_kp_in_tool_message(self) -> None:
        """Extracts knowledge points JSON from ToolMessage."""
        kp_json = '[{"name":"KP1","description":"desc","tags":[]}]'
        extract_tc = {
            "name": "extract_knowledge_points",
            "args": {},
            "id": "t1",
            "type": "tool_call",
        }
        messages: list[object] = [
            HumanMessage(content="text"),
            AIMessage(content="", tool_calls=[extract_tc]),
            ToolMessage(content=kp_json, name="extract_knowledge_points", tool_call_id="t1"),
        ]
        result = _extract_kp_from_history(messages)  # type: ignore[arg-type]
        assert result == kp_json

    def test_returns_none_when_no_kp(self) -> None:
        """Returns None when no knowledge point ToolMessage exists."""
        messages: list[object] = [
            HumanMessage(content="hello"),
            AIMessage(content="hi"),
        ]
        result = _extract_kp_from_history(messages)  # type: ignore[arg-type]
        assert result is None

    def test_returns_none_for_empty_kp_list(self) -> None:
        """Returns None when knowledge points list is empty."""
        messages: list[object] = [
            ToolMessage(content="[]", name="extract_knowledge_points", tool_call_id="t1"),
        ]
        result = _extract_kp_from_history(messages)  # type: ignore[arg-type]
        assert result is None


# --- Graph structure test ---


class TestDispatchGraphStructure:
    @pytest.mark.asyncio
    async def test_graph_has_dispatch_node(self) -> None:
        """Compiled graph includes dispatch node."""
        with patch.object(chat_graph.settings, "chat_db_path", _TEST_DB):
            graph = await create_chat_graph()
        assert "dispatch" in graph.nodes

    @pytest.mark.asyncio
    async def test_graph_has_all_three_nodes(self) -> None:
        """Compiled graph has dispatch, chat, and tools nodes."""
        with patch.object(chat_graph.settings, "chat_db_path", _TEST_DB):
            graph = await create_chat_graph()
        for node in ("dispatch", "chat", "tools"):
            assert node in graph.nodes
