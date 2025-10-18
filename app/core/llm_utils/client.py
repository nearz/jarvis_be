from functools import lru_cache
from langchain_openai import ChatOpenAI


@lru_cache
def get_llm_client(model: str = "gpt-4o-mini", temperature: float = 0.7):
    return ChatOpenAI(model=model, temperature=temperature)
