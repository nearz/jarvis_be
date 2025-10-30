import logging
from uuid import uuid4
from typing import Union
import asyncio

from aiosqlite import IntegrityError, OperationalError, DatabaseError, ProgrammingError
from tenacity import (
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception,
)

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, AIMessageChunk
from langgraph.graph.state import CompiledStateGraph, RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from ..agent.state import AgentState, ContextSchema
from ..core.llm_utils.title_generator import generate_chat_title
from ..core.llm_utils.normalize import get_msg_content_text
from ..core.db_ops.app_db import AppDatabase, DatabaseException, MessageType
from ..core.db_ops.agent_checkpoints_db import (
    CheckpointDatabaseException,
    thread_msg_list,
)
from ..core.logging import get_logger
from ..core.utils.file_logging import log_failed_persistence
from ..models.controller_models import ErrorType
from ..models.controller_models import (
    ContentStreamChunk,
    ErrorStreamChunk,
    DoneStreamChunk,
)

logger = get_logger(__name__)
retry_logger = logging.getLogger(__name__)


async def chat_controller(
    message: str,
    llm: str,
    user_id: str,
    app_db: AppDatabase,
    saver: AsyncSqliteSaver,
    graph: CompiledStateGraph[AgentState, ContextSchema, AgentState, AgentState],
    *,
    thread_id: Union[str, None],
):
    new_thread = False
    if not thread_id:
        thread_id = str(uuid4())
        new_thread = True
        logger.info("New thread created | thread_id: %s", thread_id)

    try:
        human_msg = HumanMessage(message)
        logger.debug(
            "Invoking graph | thread_id: %s | message preview: %s",
            thread_id,
            message[:100],
        )
        config = RunnableConfig({"configurable": {"thread_id": thread_id}})
        context = ContextSchema(llm)

        async for msg, _ in graph.astream(
            {"messages": [human_msg]},
            config=config,
            context=context,
            stream_mode="messages",
        ):
            if isinstance(msg, AIMessageChunk):
                # TODO: When type of content is list[str|dict]
                if isinstance(msg.content, str):
                    yield ContentStreamChunk(text=msg.content)
                else:
                    logger.debug(
                        "msg content not just a string | content: %s", str(msg.content)
                    )

        yield DoneStreamChunk(thread_id=thread_id)
        logger.info("Graph execution complete | thread_id: %s", thread_id)

        asyncio.create_task(
            _thread_persistence_with_fallback(
                thread_id, user_id, llm, new_thread, app_db, saver
            )
        )

    except TimeoutError as e:
        logger.exception("Timeout error | thread_id: %s", thread_id)
        yield ErrorStreamChunk(message="Graph execution timeout")

    except Exception as e:
        logger.exception(
            "Unexpected system error | thread_id: %s | error: %s",
            thread_id,
            str(e),
        )
        yield ErrorStreamChunk(message="Unexpected system error")


async def _thread_persistence_with_fallback(
    thread_id: str,
    user_id: str,
    llm: str,
    new_thread: bool,
    app_db: AppDatabase,
    saver: AsyncSqliteSaver,
):
    try:
        await asyncio.wait_for(
            _thread_persistence(thread_id, user_id, llm, new_thread, app_db, saver),
            timeout=60.0,
        )
        logger.info("Thread persisted successfully | thread_id: %s", thread_id)

    except asyncio.TimeoutError as e:
        logger.critical(
            "Thread persistence timeout | thread_id: %s | user_id: %s | "
            "exceeded 60 seconds",
            thread_id,
            user_id,
        )
        log_failed_persistence(
            thread_id=thread_id,
            user_id=user_id,
            llm=llm,
            new_thread=new_thread,
            error=e,
            error_type="timeout",
        )

    except Exception as e:
        # Determine error category for better logging
        error_category = "unknown"
        if isinstance(e, (IntegrityError, ProgrammingError)):
            error_category = "permanent_error"
        elif isinstance(e, OperationalError):
            error_category = "operational_error"
        elif isinstance(e, DatabaseException):
            error_category = "database_error"
        elif isinstance(e, CheckpointDatabaseException):
            error_category = "langgraph_checkpoint_db_error"

        logger.critical(
            "Thread persistence failed after retries | thread_id: %s | "
            "user_id: %s | error_category: %s | error: %s",
            thread_id,
            user_id,
            error_category,
            str(e),
        )
        log_failed_persistence(
            thread_id=thread_id,
            user_id=user_id,
            llm=llm,
            new_thread=new_thread,
            error=e,
            error_type=error_category,
        )


# NOTE: Not going to put a big effort in defining retryable db exceptions
# May change if moving this to postgres. But retry pattern is here to
# pick up and change as needed.
def _should_retry(exception) -> bool:
    if isinstance(exception, ValueError):
        return False

    if isinstance(exception, IntegrityError):
        return False

    if isinstance(exception, ProgrammingError):
        return False

    if isinstance(exception, OperationalError):
        retryable = [
            "SQLITE_BUSY",
            "SQLITE_LOCKED",
            "SQLITE_IOERR_BLOCKED",
            "SQLITE_IOERR_BUSY",
        ]
        exc_name = getattr(exception, "sqlite_errorname", None)
        if exc_name and exc_name in retryable:
            return True
        return False

    if isinstance(exception, CheckpointDatabaseException):
        return True

    if isinstance(exception, DatabaseException):
        if exception.__cause__:
            return _should_retry(exception.__cause__)
        return False

    return False


@retry(
    stop=stop_after_attempt(5),
    retry=retry_if_exception(_should_retry),
    wait=wait_random_exponential(multiplier=1, max=10),
    before_sleep=before_sleep_log(retry_logger, logging.INFO),
    reraise=True,
)
async def _thread_persistence(
    thread_id: str,
    user_id: str,
    llm: str,
    new_thread: bool,
    app_db: AppDatabase,
    saver: AsyncSqliteSaver,
) -> None:

    logger.debug("Start thread persistence | thread_id: %s", thread_id)
    msg_list = await thread_msg_list(thread_id, saver)
    if msg_list is None:
        raise CheckpointDatabaseException("Could not fetch checkpoint thread messages")

    last_human_msg = _get_last_human_message(msg_list)
    if not last_human_msg or not isinstance(last_human_msg.id, str):
        raise ValueError("Invalid human message or missing message ID")

    last_ai_msg = _get_last_ai_message(msg_list)
    if not last_ai_msg or not isinstance(last_ai_msg.id, str):
        raise ValueError("Invalid AI message or missing message ID")

    human_msg_txt = get_msg_content_text(last_human_msg.content)
    ai_msg_txt = get_msg_content_text(last_ai_msg.content)

    title = ""
    if new_thread:
        title = await generate_chat_title(human_msg_txt, ai_msg_txt)

    async with app_db.transaction():
        if new_thread:
            await app_db.create_user_thread(user_id, thread_id, title, llm)
        else:
            await app_db.set_thread_updated(user_id, thread_id, llm)

        await app_db.create_thread_msg(
            human_msg_txt,
            MessageType.USER.value,
            llm,
            last_human_msg.id,
            thread_id,
        )

        await app_db.create_thread_msg(
            ai_msg_txt,
            MessageType.AI.value,
            llm,
            last_ai_msg.id,
            thread_id,
        )
    logger.info("Thread persistence successful | thread_id: %s", thread_id)


def _get_last_human_message(messages: list[BaseMessage]) -> Union[HumanMessage, None]:
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg
    return None


def _get_last_ai_message(messages: list[BaseMessage]) -> Union[AIMessage, None]:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return msg
    return None
