"""LangGraph StateGraph with GLM-5 chat node and tool nodes."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from pydantic import SecretStr

from question_agent.chat.tools import ALL_TOOLS
from question_agent.config import settings

_ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"

_checkpointer: MemorySaver | None = None


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


async def chat_node(state: MessagesState) -> dict[str, list[BaseMessage]]:
    """Chat node: invoke GLM-5 with accumulated messages and return the response."""
    llm = _create_llm_with_tools()
    response = await llm.ainvoke(state["messages"])
    return {"messages": [response]}


def get_checkpointer() -> MemorySaver:
    """Return a singleton MemorySaver for checkpoint storage."""
    global _checkpointer  # noqa: PLW0603
    if _checkpointer is None:
        _checkpointer = MemorySaver()
    return _checkpointer


def create_chat_graph() -> CompiledStateGraph[MessagesState, None, MessagesState, MessagesState]:
    """Build and compile the chat StateGraph with MemorySaver checkpointer."""
    graph = StateGraph(MessagesState)
    graph.add_node("chat", chat_node)
    graph.add_node("tools", ToolNode(ALL_TOOLS))
    graph.add_edge(START, "chat")
    graph.add_edge("chat", END)
    return graph.compile(checkpointer=get_checkpointer())
