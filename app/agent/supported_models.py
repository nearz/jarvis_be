from pydantic import BaseModel, Field, ValidationError
from typing import Literal


class ModelConfig(BaseModel):
    provider: Literal["openai", "anthropic"]
    model: str
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
        "provider_string": "openai",
        "model_string": "gpt-4o",
        "tool_support": True,
    },
    "gpt-4o-mini": {
        "provider_string": "openai",
        "model_string": "gpt-4o-mini",
        "tool_support": True,
    },
    "gpt-4.1": {
        "provider_string": "openai",
        "model_string": "gpt-4.1",
        "tool_support": True,
    },
    "gpt-4.1-mini": {
        "provider_string": "openai",
        "model_string": "gpt-4.1-mini",
        "tool_support": True,
    },
    "gpt-4.1-nano": {
        "provider_string": "openai",
        "model_string": "gpt-4.1-nano",
        "tool_support": True,
    },
    "claude-opus-4-1": {
        "provider_string": "anthropic",
        "model_string": "claude-opus-4-1",
        "tool_support": True,
    },
    "claude-haiku-4-5": {
        "provider_string": "anthropic",
        "model_string": "claude-haiku-4-5",
        "tool_support": True,
    },
    "claude-sonnet-4-5": {
        "provider_string": "anthropic",
        "model_string": "claude-sonnet-4-5",
        "tool_support": True,
    },
}

supported_models = validate_models(supported_models_raw)
