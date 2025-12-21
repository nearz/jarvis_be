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


async def delete_checkpoint_threads_bulk(
    thread_ids: list[str], saver: AsyncSqliteSaver, batch_size: int = 100
) -> None:
    try:
        if not thread_ids:
            return

        for i in range(0, len(thread_ids), batch_size):
            batch = thread_ids[i : i + batch_size]
            placeholders = ",".join("?" * len(batch))

            async with saver.lock, saver.conn.cursor() as cur:
                await cur.execute(
                    f"DELETE FROM checkpoints WHERE thread_id IN ({placeholders})",
                    batch,
                )
                await cur.execute(
                    f"DELETE FROM writes WHERE thread_id IN ({placeholders})", batch
                )
                await saver.conn.commit()

    except Exception as e:
        logger.exception("Bulk delete threads: Unexpected system error")
        raise
