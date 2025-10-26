from uuid import uuid4
from typing import Union

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
from ..models.controller_models import ChatResult, ErrorType
from ..models.controller_models import (
    ContentStreamChunk,
    ErrorStreamChunk,
    DoneStreamChunk,
)

logger = get_logger(__name__)


# TODO: After async iterator completes succesfully synce app db messages with checkpoint db.
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

        logger.info("Graph execution complete | thread_id: %s", thread_id)

        yield DoneStreamChunk(thread_id=thread_id)

        result = await _thread_persistence(
            thread_id, user_id, llm, new_thread, app_db, saver
        )
        if not result:
            logger.debug("Failed to persist thread to App DB, needs investigation")

    except TimeoutError as e:
        logger.exception("Timeout error | thread_id: %s", thread_id)
        yield ErrorStreamChunk(message="Graph execution timeout")

    except Exception as e:
        logger.exception(
            "Graph execution failed | thread_id: %s | error: %s",
            thread_id,
            str(e),
        )
        yield ErrorStreamChunk(message="Unexpected system error")


# TODO: Raising exceptions and returning bool for now, review for improvement.
# TODO: Database operations more atomic?
async def _thread_persistence(
    thread_id: str,
    user_id: str,
    llm: str,
    new_thread: bool,
    app_db: AppDatabase,
    saver: AsyncSqliteSaver,
) -> bool:
    msg_list = await thread_msg_list(thread_id, saver)
    if msg_list is None:
        raise CheckpointDatabaseException("Could not fetch checkpoint thread messages")

    last_human_msg = _get_last_human_message(msg_list)
    last_ai_msg = _get_last_ai_message(msg_list)

    if not last_human_msg or not isinstance(last_human_msg.id, str):
        raise ValueError("Invalid human message or missing message ID")

    if not last_ai_msg or not isinstance(last_ai_msg.id, str):
        raise ValueError("Invalid AI message or missing message ID")

    human_msg_txt = get_msg_content_text(last_human_msg.content)
    ai_msg_txt = get_msg_content_text(last_ai_msg.content)

    # New Thread
    # Generate title, create thread, save messages, thread updated at
    if new_thread:
        title = await generate_chat_title(human_msg_txt, ai_msg_txt)
        res = await app_db.create_user_thread(user_id, thread_id, title, llm)
        if not res:
            logger.error(
                "Failed to create user thread | user_id: %s | thread_id: %s",
                user_id,
                thread_id,
            )
            return False

    # Existing Thread
    # save messages, thread updated at
    msg_one_res = await app_db.create_thread_msg(
        human_msg_txt,
        MessageType.USER.value,
        llm,
        last_human_msg.id,
        thread_id,
    )

    msg_two_res = await app_db.create_thread_msg(
        ai_msg_txt,
        MessageType.AI.value,
        llm,
        last_ai_msg.id,
        thread_id,
    )
    if not (msg_one_res and msg_two_res):
        return False

    return True


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
