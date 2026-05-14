"""LangGraph StateGraph with dispatch + ReAct agent loop."""

from __future__ import annotations

import json
import logging
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

logger = logging.getLogger(__name__)

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
        logger.debug("dispatch_node: no user message found")
        return {"messages": []}

    raw_content = str(last_user_msg.content)

    # Parse kb_id prefix like [kb:abc123]
    kb_id: str | None = None
    kb_match = _KB_PREFIX_RE.match(raw_content)
    if kb_match:
        kb_id = kb_match.group(1)
        raw_content = _KB_PREFIX_RE.sub("", raw_content)

    intent = classify_intent(raw_content)
    logger.info("dispatch_node: content=%r, kb_id=%s, intent=%s", raw_content, kb_id, intent)

    if intent == "chat":
        logger.info("dispatch_node: routing to chat_node (no forced tool call)")
        return {"messages": []}

    # Force tool call by creating a synthetic AIMessage
    extra_messages: list[BaseMessage] = []

    if intent == "extract":
        tool_name = _TOOL_NAME_MAP["extract"]
        tool_args = {"text": raw_content}
    elif intent == "generate":
        # If kb_id is present, fetch KPs from KB instead of history
        if kb_id:
            tool_name = _TOOL_NAME_MAP["fetch_kb"]
            tool_args = {"kb_id": kb_id}
            logger.info("dispatch_node: forcing fetch_knowledge_points_from_kb(kb_id=%s)", kb_id)
        else:
            # For generate without KB, check if KPs exist in prior messages
            kp_json = _extract_kp_from_history(list(state["messages"]))
            if kp_json is None:
                logger.info("dispatch_node: generate intent but no prior KPs, asking for material")
                hint = SystemMessage(
                    content="用户想要出题，但还没有提取知识点。请先询问用户是否需要提供教材内容来提取知识点。"
                )
                return {"messages": [hint]}
            tool_name = _TOOL_NAME_MAP["generate"]
            tool_args = {"knowledge_points_json": kp_json}
            qtype = detect_question_type(raw_content)
            if qtype:
                tool_args["question_type"] = qtype
            logger.info(
                "dispatch_node: forcing generate_questions(kp_count=%d, qtype=%s)",
                len(json.loads(kp_json)),
                qtype,
            )
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
    logger.info(
        "dispatch_node: forced tool_call name=%s args_keys=%s",
        tool_name,
        list(tool_args.keys()),
    )
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
    msg_count = len(state["messages"])
    logger.info("chat_node: invoking LLM with %d messages", msg_count)
    for i, msg in enumerate(state["messages"]):
        content_preview = str(msg.content)[:200] if msg.content else "(empty)"
        tool_calls_info = ""
        if isinstance(msg, AIMessage) and msg.tool_calls:
            tool_calls_info = f" tool_calls={[tc['name'] for tc in msg.tool_calls]}"
        logger.debug(
            "chat_node: msg[%d] type=%s%s content=%.100s",
            i,
            type(msg).__name__,
            tool_calls_info,
            content_preview,
        )
    response = await llm.ainvoke(state["messages"])
    resp_preview = str(response.content)[:200] if response.content else "(empty)"
    tc_info = ""
    if isinstance(response, AIMessage) and response.tool_calls:
        tc_info = f" tool_calls={[tc['name'] for tc in response.tool_calls]}"
    logger.info("chat_node: LLM response%s content=%.100s", tc_info, resp_preview)
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
