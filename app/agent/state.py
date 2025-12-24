from dataclasses import dataclass
from typing import Annotated, TypedDict, Sequence, Union

from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
from langgraph.graph import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from .model import get_model
from .tools import get_tools
from ..core.logging import get_logger
from ..core.llm_utils.prompts import GENERAL_SYSTEM_PROMPT, project_inst_sys_prompt

logger = get_logger(__name__)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


@dataclass
class ContextSchema:
    llm: str
    client_timestamp: str
    project_title: Union[str, None]
    project_instructions: Union[str, None]


async def call_llm(state: AgentState, runtime: Runtime[ContextSchema]) -> AgentState:
    logger.debug("LLM call started | llm: %s", runtime.context.llm)
    logger.debug("Client Timestamp | ts: %s", runtime.context.client_timestamp)

    date_sys_prompt = SystemMessage(
        f"REFERENCE_TIME={runtime.context.client_timestamp}"
    )
    gen_sys_prompt = SystemMessage(GENERAL_SYSTEM_PROMPT)
    sys_prompts = [date_sys_prompt, gen_sys_prompt]

    if runtime.context.project_title is not None:
        title = runtime.context.project_title
        inst = runtime.context.project_instructions
        proj_sys_prompt = SystemMessage(project_inst_sys_prompt(title, inst))
        sys_prompts.append(proj_sys_prompt)

    llm = get_model(runtime.context.llm)
    all_msgs = sys_prompts + list(state["messages"])
    response = await llm.ainvoke(all_msgs)

    # TODO: Should add llm response when logging to file?
    logger.debug(
        "LLM response received | llm: %s",
        runtime.context.llm,
    )

    return {"messages": [response]}


def should_continue(state: AgentState) -> bool:
    """Returns True if the last message has tool calls, False otherwise"""
    msgs = state["messages"]
    if not msgs:
        return False
    last_msg = msgs[-1]
    has_tool_calls = isinstance(last_msg, AIMessage) and bool(
        getattr(last_msg, "tool_calls", None)
    )

    if has_tool_calls:
        logger.debug(
            "Tool calls detected | tool calls: %s",
            getattr(last_msg, "tool_calls", None),
        )
    else:
        logger.debug("No tool calls detected")

    return has_tool_calls


def build_graph(
    saver: AsyncSqliteSaver,
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
