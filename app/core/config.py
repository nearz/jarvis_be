from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    APP_TITLE: str
    APP_DESCRIPTION: str
    APP_VER: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    TOKEN_EXP: int

    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"

    TAVILY_API_KEY: str
    TAVILY_MAX_RESULTS: int = 5
    TAVILY_SEARCH_TIMEOUT: int = 15
    TAVILY_EXTRACT_TIMEOUT: float = 15.0

    ANTHROPIC_API_KEY: str

    DEFAULT_CHAT_TITLE: str = "Jarvis Chat"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
