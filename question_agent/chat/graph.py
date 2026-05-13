"""LangGraph StateGraph with dispatch + ReAct agent loop."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from pydantic import SecretStr

from question_agent.chat.intent import classify_intent, detect_question_type
from question_agent.chat.tools import ALL_TOOLS
from question_agent.config import settings

_ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"

_checkpointer: AsyncSqliteSaver | None = None
_db_conn: Any = None

_TOOL_NAME_MAP: dict[str, str] = {
    "extract": "extract_knowledge_points",
    "generate": "generate_questions",
    "fetch_kb": "fetch_knowledge_points_from_kb",
}

_KB_PREFIX_RE = re.compile(r"^\[kb:([a-f0-9]+)\]\s*")


def _create_llm() -> ChatOpenAI:
    """Create a ChatOpenAI instance configured for ZhipuAI GLM API."""
    return ChatOpenAI(
        model=settings.glm_model,
        api_key=SecretStr(settings.glm_api_key),
        base_url=_ZHIPU_BASE_URL,
        streaming=True,
    )


def _create_llm_with_tools() -> Any:
    """Create a ChatOpenAI instance with tools bound for agent use."""
    return _create_llm().bind_tools(ALL_TOOLS)


async def dispatch_node(state: MessagesState) -> dict[str, list[BaseMessage]]:
    """Classify intent and force tool call for extract/generate, passthrough for chat."""
    # Find the last user message
    last_user_msg: HumanMessage | None = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_user_msg = msg
            break

    if last_user_msg is None:
        return {"messages": []}

    content = str(last_user_msg.content)

    # Parse kb_id prefix like [kb:abc123]
    kb_id: str | None = None
    kb_match = _KB_PREFIX_RE.match(content)
    if kb_match:
        kb_id = kb_match.group(1)
        content = _KB_PREFIX_RE.sub("", content)

    intent = classify_intent(content)

    if intent == "chat":
        return {"messages": []}

    # Force tool call by creating a synthetic AIMessage
    extra_messages: list[BaseMessage] = []

    if intent == "extract":
        tool_name = _TOOL_NAME_MAP["extract"]
        tool_args = {"text": content}
    elif intent == "generate":
        # If kb_id is present, fetch KPs from KB instead of history
        if kb_id:
            tool_name = _TOOL_NAME_MAP["fetch_kb"]
            tool_args = {"kb_id": kb_id}
        else:
            # For generate without KB, check if KPs exist in prior messages
            kp_json = _extract_kp_from_history(list(state["messages"]))
            if kp_json is None:
                hint = SystemMessage(
                    content="用户想要出题，但还没有提取知识点。请先询问用户是否需要提供教材内容来提取知识点。"
                )
                return {"messages": [hint]}
            tool_name = _TOOL_NAME_MAP["generate"]
            tool_args = {"knowledge_points_json": kp_json}
            qtype = detect_question_type(content)
            if qtype:
                tool_args["question_type"] = qtype
    else:
        return {"messages": []}

    tool_call = {
        "name": tool_name,
        "args": tool_args,
        "id": f"forced_{intent}",
        "type": "tool_call",
    }
    synthetic_ai = AIMessage(content="", tool_calls=[tool_call])
    extra_messages.append(synthetic_ai)
    return {"messages": extra_messages}


def _extract_kp_from_history(messages: list[BaseMessage]) -> str | None:
    """Try to find knowledge points JSON from prior tool results in conversation."""
    from langchain_core.messages import ToolMessage

    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and msg.name == "extract_knowledge_points":
            content = str(msg.content)
            try:
                data = json.loads(content)
                if isinstance(data, list) and len(data) > 0:
                    return content
            except (json.JSONDecodeError, TypeError):
                continue
    return None


def _should_continue(state: MessagesState) -> Literal["tools", "__end__"]:
    """Conditional edge: route to tools if the last AI message has tool_calls."""
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "__end__"


def _route_after_dispatch(state: MessagesState) -> Literal["tools", "chat"]:
    """After dispatch, route to tools if a forced tool call was injected, else to chat."""
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "chat"


async def chat_node(state: MessagesState) -> dict[str, list[BaseMessage]]:
    """Chat node: invoke GLM-5 with accumulated messages and return the response."""
    llm = _create_llm_with_tools()
    response = await llm.ainvoke(state["messages"])
    return {"messages": [response]}


async def get_checkpointer() -> AsyncSqliteSaver:
    """Return a singleton AsyncSqliteSaver for checkpoint storage."""
    global _checkpointer, _db_conn  # noqa: PLW0603
    if _checkpointer is None:
        import aiosqlite

        db_path = settings.chat_db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _db_conn = await aiosqlite.connect(str(db_path))
        _checkpointer = AsyncSqliteSaver(conn=_db_conn)
        await _checkpointer.setup()
    return _checkpointer


_ChatGraph = CompiledStateGraph[MessagesState, None, MessagesState, MessagesState]


async def create_chat_graph() -> _ChatGraph:
    """Build and compile the StateGraph with dispatch + ReAct agent loop."""
    graph = StateGraph(MessagesState)
    graph.add_node("dispatch", dispatch_node)
    graph.add_node("chat", chat_node)
    graph.add_node("tools", ToolNode(ALL_TOOLS))

    graph.add_edge(START, "dispatch")
    graph.add_conditional_edges(
        "dispatch", _route_after_dispatch, {"tools": "tools", "chat": "chat"}
    )
    graph.add_conditional_edges("chat", _should_continue, {"tools": "tools", "__end__": END})
    graph.add_edge("tools", "chat")

    return graph.compile(checkpointer=await get_checkpointer())
