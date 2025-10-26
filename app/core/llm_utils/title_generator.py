from langchain_core.messages import HumanMessage

from .normalize import get_msg_content_text
from .client import get_llm_client
from .prompts import TITLE_GEN_PROMPT
from ..config import settings
from ..logging import get_logger

logger = get_logger(__name__)


async def generate_chat_title(
    human_msg: str, ai_msg: str, model: str = "gpt-4o-mini"
) -> str:
    try:
        if not human_msg or not ai_msg:
            logger.debug("No human message or ai response message")
            return settings.DEFAULT_CHAT_TITLE

        human_msg = "User: " + human_msg
        ai_msg = "Assistant: " + ai_msg
        convo = human_msg + "\n" + ai_msg

        client = get_llm_client(model=model, temperature=0.7)
        prompt = TITLE_GEN_PROMPT.format(conversation_preview=convo)

        response = await client.ainvoke([HumanMessage(content=prompt)])

        content = get_msg_content_text(response.content)
        title = content.strip().strip('"').strip("'")
        logger.debug("Title generated: %s", title)
        return title or settings.DEFAULT_CHAT_TITLE

    except Exception as e:
        logger.exception("Exception occurred in title generation")
        return settings.DEFAULT_CHAT_TITLE
