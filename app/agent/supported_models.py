from pydantic import BaseModel, Field, ValidationError
from typing import Literal


class ModelConfig(BaseModel):
    provider: Literal["openai", "anthropic"]
    provider_display_name: str
    model: str
    display_name: str
    tool_support: bool


def validate_models(models: dict) -> dict[str, ModelConfig]:
    validated = {}
    errs = []

    for model_name, config in models.items():
        try:
            validated[model_name] = ModelConfig(**config)
        except ValidationError as e:
            errs.append(f"Invalid config for '{model_name}': {e}")

    if errs:
        raise ValueError("Model configuration failed: \n" + "\n".join(errs))

    return validated


supported_models_raw = {
    "gpt-4o": {
        "provider": "openai",
        "provider_display_name": "OpenAI",
        "model": "gpt-4o",
        "display_name": "GPT 4o",
        "tool_support": True,
    },
    "gpt-4o-mini": {
        "provider": "openai",
        "provider_display_name": "OpenAI",
        "model": "gpt-4o-mini",
        "display_name": "GPT 4o Mini",
        "tool_support": True,
    },
    "gpt-4.1": {
        "provider": "openai",
        "provider_display_name": "OpenAI",
        "model": "gpt-4.1",
        "display_name": "GPT 4.1",
        "tool_support": True,
    },
    "gpt-4.1-mini": {
        "provider": "openai",
        "provider_display_name": "OpenAI",
        "model": "gpt-4.1-mini",
        "display_name": "GPT 4.1 Mini",
        "tool_support": True,
    },
    "gpt-4.1-nano": {
        "provider": "openai",
        "provider_display_name": "OpenAI",
        "model": "gpt-4.1-nano",
        "display_name": "GPT 4.1 Nano",
        "tool_support": True,
    },
    "claude-opus-4-1": {
        "provider": "anthropic",
        "provider_display_name": "Anthropic",
        "model": "claude-opus-4-1",
        "display_name": "Claude Opus 4.1",
        "tool_support": True,
    },
    "claude-haiku-4-5": {
        "provider": "anthropic",
        "provider_display_name": "Anthropic",
        "model": "claude-haiku-4-5",
        "display_name": "Claude Haiku 4.5",
        "tool_support": True,
    },
    "claude-sonnet-4-5": {
        "provider": "anthropic",
        "provider_display_name": "Anthropic",
        "model": "claude-sonnet-4-5",
        "display_name": "Claude Sonnet 4.5",
        "tool_support": True,
    },
}

supported_models = validate_models(supported_models_raw)
