from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    APP_TITLE: str
    APP_DESCRIPTION: str
    APP_VER: str

    TAVILY_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
