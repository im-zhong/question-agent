"""LangGraph StateGraph with single GLM-5 chat node."""

from __future__ import annotations

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import SecretStr

from question_agent.config import settings

_ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"

_checkpointer: MemorySaver | None = None


def _create_llm() -> ChatOpenAI:
    """Create a ChatOpenAI instance configured for ZhipuAI GLM API."""
    return ChatOpenAI(
        model=settings.glm_model,
        api_key=SecretStr(settings.glm_api_key),
        base_url=_ZHIPU_BASE_URL,
    )


async def chat_node(state: MessagesState) -> dict[str, list[BaseMessage]]:
    """Chat node: invoke GLM-5 with accumulated messages and return the response."""
    llm = _create_llm()
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
    graph.add_edge(START, "chat")
    graph.add_edge("chat", END)
    return graph.compile(checkpointer=get_checkpointer())
