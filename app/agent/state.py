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


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


@dataclass
class ContextSchema:
    llm: str


# TODO: Remove pretty print for logging
def call_llm(state: AgentState, runtime: Runtime[ContextSchema]) -> AgentState:
    system_prompt = SystemMessage(
        "You are an AI assistant, plese answer my query to the best of your ability"
    )

    llm = get_model_with_tools(runtime.context.llm)
    all_msgs = [system_prompt] + list(state["messages"])
    response = llm.invoke(all_msgs)
    response.pretty_print()
    return {"messages": [response]}


def should_continue(state: AgentState) -> bool:
    last_msg = state["messages"][-1]
    tool_call = False
    if isinstance(last_msg, AIMessage):
        if last_msg.tool_calls:
            tool_call = True
            return tool_call
    return tool_call


def build_graph(
    checkpointer,
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

    return graph.compile(checkpointer=checkpointer)
