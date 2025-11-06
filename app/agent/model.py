from typing import Union
from functools import lru_cache
from langchain_openai import ChatOpenAI
from langgraph.graph.state import Runnable
from langchain_core.language_models import BaseChatModel
from langchain.chat_models import init_chat_model
from .supported_models import supported_models

from .tools import get_tools
from ..core.logging import get_logger

logger = get_logger(__name__)


class ModelException(Exception):
    pass


@lru_cache(maxsize=8)
def get_model(input_model: str) -> Union[BaseChatModel, Runnable]:
    model_config = supported_models.get(input_model, None)

    if model_config is None:
        raise ValueError(f"Unsupported llm: {input_model}")

    try:
        model_str = f"{model_config.provider}:{model_config.model}"
        init_model = init_chat_model(model_str)
        if model_config.tool_support:
            return init_model.bind_tools(get_tools())
        return init_model
    except Exception as e:
        logger.exception("Error occurred initializing model | llm: %s", input_model)
        raise ModelException(
            "An exception has occured during llm model initialization"
        ) from e
