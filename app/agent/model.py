from typing import Union
from functools import lru_cache
from langchain_openai import ChatOpenAI
from langgraph.graph.state import Runnable
from langchain_core.language_models import BaseChatModel
from langchain.chat_models import init_chat_model
from .supported_models import supported_models

from .tools import get_tools


@lru_cache(maxsize=8)
def get_model(input_model: str) -> Union[BaseChatModel, Runnable]:
    model = supported_models.get(input_model, None)

    if model is None:
        raise ValueError(f"Unsupported llm: {input_model}")

    model_str = f"{model['provider_string']}:{model['model_string']}"
    init_model = init_chat_model(model_str)
    if model["tool_support"]:
        return init_model.bind_tools(get_tools())
    return init_model
