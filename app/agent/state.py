from dataclasses import dataclass
from typing import Annotated, TypedDict, Sequence

from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
from langgraph.graph import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.prebuilt import ToolNode

from .model import get_model_with_tools
from .tools import get_tools
from ..core.logging import get_logger

logger = get_logger(__name__)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


@dataclass
class ContextSchema:
    llm: str


async def call_llm(state: AgentState, runtime: Runtime[ContextSchema]) -> AgentState:
    logger.debug("LLM call started | llm: %s", runtime.context.llm)

    system_prompt = SystemMessage(
        "You are an AI assistant, please answer my query to the best of your ability"
    )

    llm = get_model_with_tools(runtime.context.llm)
    all_msgs = [system_prompt] + list(state["messages"])
    response = await llm.ainvoke(all_msgs)

    logger.debug(
        "LLM response received | llm: %s | ai message preview: %s",
        runtime.context.llm,
        response.content if response.content else "",
    )

    return {"messages": [response]}


def should_continue(state: AgentState) -> bool:
    """Returns True if the last message has tool calls, False otherwise"""
    last_msg = state["messages"][-1]
    has_tool_calls = isinstance(last_msg, AIMessage) and bool(last_msg.tool_calls)

    if has_tool_calls:
        logger.debug("Tool calls detected | tool calls: %s", last_msg.tool_calls)

    return has_tool_calls


def build_graph(
    saver,
) -> CompiledStateGraph[AgentState, ContextSchema, AgentState, AgentState]:
    graph = StateGraph(AgentState, context_schema=ContextSchema)
    graph.add_node("call_llm", call_llm)
    graph.add_node("tools", ToolNode(tools=get_tools()))

    graph.add_edge(START, "call_llm")
    graph.add_conditional_edges(
        "call_llm",
        should_continue,
        {
            True: "tools",
            False: END,
        },
    )
    graph.add_edge("tools", "call_llm")

    return graph.compile(checkpointer=saver)
