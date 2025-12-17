from dataclasses import dataclass
from typing import Annotated, TypedDict, Sequence, Union

from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
from langgraph.graph import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.prebuilt import ToolNode

from .model import get_model
from .tools import get_tools
from ..core.logging import get_logger
from ..core.llm_utils.prompts import system_prompt_gen

logger = get_logger(__name__)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


@dataclass
class ContextSchema:
    llm: str
    project_instructions: Union[str, None]


async def call_llm(state: AgentState, runtime: Runtime[ContextSchema]) -> AgentState:
    logger.debug("LLM call started | llm: %s", runtime.context.llm)

    system_prompt = system_prompt_gen(runtime.context.project_instructions)
    final_sys_prompt = SystemMessage(system_prompt)

    llm = get_model(runtime.context.llm)
    all_msgs = [final_sys_prompt] + list(state["messages"])
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
    else:
        logger.debug("No tool calls detected")

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
