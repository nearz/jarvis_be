from typing import Union
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain_core.messages import BaseMessage
from langgraph.graph.state import RunnableConfig

from ..logging import get_logger

logger = get_logger(__name__)


class CheckpointDatabaseException(Exception):
    """Raised when accessing checkpoint fails"""


async def thread_msg_list(
    thread_id: str, saver: AsyncSqliteSaver
) -> Union[list[BaseMessage], None]:
    try:
        config = RunnableConfig({"configurable": {"thread_id": thread_id}})
        checkpoint = await saver.aget(config=config)

        return checkpoint["channel_values"]["messages"] if checkpoint else None

    except Exception as e:
        logger.exception("Fetching checkpoint messages: Unexpected system error")
        raise


async def delete_checkpoint_thread(thread_id: str, saver: AsyncSqliteSaver) -> None:
    try:
        await saver.adelete_thread(thread_id)
    except Exception as e:
        logger.exception("Fetching checkpoint messages: Unexpected system error")
        raise
