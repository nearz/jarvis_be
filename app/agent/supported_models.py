"""
OpenAI:
gpt-4o
gpt-4o-mini
gpt-4.1
gpt-4.1-mini
gpt-4.1-nano

Anthropic:
claude-sonnet-4-5
claude-haiku-4-5
claude-opus-4-1
"""

supported_models = {
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
