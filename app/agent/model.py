from langchain_openai import ChatOpenAI
from langgraph.graph.state import Runnable

from .tools import get_tools

# TODO: Handle different models, OpenAI, Anthropic, Gemeni...


def get_model_with_tools(model: str) -> Runnable:
    return ChatOpenAI(model=model).bind_tools(get_tools())
