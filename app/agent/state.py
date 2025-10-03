from dataclasses import dataclass
from typing import Annotated, TypedDict, Sequence

from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
from langgraph.graph import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime

from .model import get_model


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


@dataclass
class ContextSchema:
    llm: str


def call_llm(state: AgentState, runtime: Runtime[ContextSchema]) -> AgentState:
    system_prompt = SystemMessage(
        "You are an AI assistant, plese answer my query to the best of your ability"
    )

    llm = get_model(runtime.context.llm)
    all_msgs = [system_prompt] + list(state["messages"])
    response = llm.invoke(all_msgs)
    return {"messages": [response]}


def build_graph(checkpointer):
    graph = StateGraph(AgentState, context_schema=ContextSchema)
    graph.add_node("call_llm", call_llm)

    graph.add_edge(START, "call_llm")
    graph.add_edge("call_llm", END)

    return graph.compile(checkpointer=checkpointer)
