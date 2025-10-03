from langchain_openai import ChatOpenAI

# TODO: Handle different models, OpenAI, Anthropic, Gemeni...


def get_model(model: str) -> ChatOpenAI:
    return ChatOpenAI(model=model)


# def get_model_with_tools(model: str):
