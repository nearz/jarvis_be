from uuid import uuid4
from typing import Union, Optional
from enum import Enum
import logging

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph.state import CompiledStateGraph, RunnableConfig

from ..agent.state import AgentState, ContextSchema
from ..core.llm_utils.title_generator import generate_chat_title
from ..core.llm_utils.normalize import get_msg_content_text
from ..core.db_ops.app_db import AppDatabase, DatabaseException, MessageType
from ..core.logging import get_logger

logger = get_logger(__name__)


class ChatErrorType(Enum):
    FORBIDDEN_ERROR = "forbidden_error"
    VALIDATION_ERROR = "validation_error"
    DATABASE_ERROR = "database_error"
    LLM_ERROR = "llm_error"
    GRAPH_EXECUTION_ERROR = "graph_execution_error"
    RESPONSE_PROCESSING_ERROR = "response_processing_error"
    SYSTEM_ERROR = "system_error"


class ChatResult:
    def __init__(
        self,
        success: bool,
        message: Optional[str] = None,
        thread_id: Optional[str] = None,
        error_type: Optional[ChatErrorType] = None,
        error_details: Optional[str] = None,
    ):
        self.success = success
        self.message = message
        self.thread_id = thread_id
        self.error_type = error_type
        self.error_details = error_details


# TODO: Is there a better way to setup ainvoke params package? Maybe a func in state.
# TODO: Consider DB operation order. LangGraph could save checkpoint, but saving to
# app db could fail then would be out of sync. Can you roll back LangGraph, or retry
# on app db?
async def chat_controller(
    message: str,
    llm: str,
    user_id: str,
    app_db: AppDatabase,
    graph: CompiledStateGraph[AgentState, ContextSchema, AgentState, AgentState],
    *,
    thread_id: Union[str, None],
) -> ChatResult:
    new_thread = False
    if not thread_id:
        thread_id = str(uuid4())
        new_thread = True
        logger.info("New thread created | thread_id: %s", thread_id)
    # else:
    #     try:
    #         vto_res = await app_db.verify_thread_ownership(user_id, thread_id)
    #     except DatabaseException as e:
    #         logger.exception(
    #             "Database exception occured | user_id: %s | thread_id: %s",
    #             user_id,
    #             thread_id,
    #         )
    #         return ChatResult(
    #             success=False,
    #             thread_id=thread_id,
    #             error_type=ChatErrorType.DATABASE_ERROR,
    #             error_details="Database exception occured",
    #         )
    #
    #     if not vto_res:
    #         logger.warning(
    #             "User does not own this thread | user_id: %s | thread_id: %s",
    #             user_id,
    #             thread_id,
    #         )
    #         return ChatResult(
    #             success=False,
    #             thread_id=thread_id,
    #             error_type=ChatErrorType.FORBIDDEN_ERROR,
    #             error_details="User does not own this thread",
    #         )
    #     logger.info("Existing thread | thread_id: %s", thread_id)

    try:
        msg = HumanMessage(message)
        logger.debug(
            "Invoking graph | thread_id: %s | message preview: %s",
            thread_id,
            message[:100],
        )
        config = RunnableConfig({"configurable": {"thread_id": thread_id}})
        context = ContextSchema(llm)

        result = await graph.ainvoke(
            {"messages": [msg]}, config=config, context=context
        )

        logger.info("Graph execution complete | thread_id: %s", thread_id)

    except TimeoutError as e:
        logger.exception("Timeout error | thread_id: %s", thread_id)
        return ChatResult(
            success=False,
            thread_id=thread_id,
            error_type=ChatErrorType.GRAPH_EXECUTION_ERROR,
            error_details="Request timed out. Please try again.",
        )

    except Exception as e:
        logger.exception(
            "Graph execution failed | thread_id: %s | error: %s",
            thread_id,
            str(e),
        )

        return ChatResult(
            success=False,
            thread_id=thread_id,
            error_type=ChatErrorType.GRAPH_EXECUTION_ERROR,
            error_details="Graph execution failure",
        )

    try:
        if not result or "messages" not in result:
            logger.error("Invalid response structure | thread_id: %s", thread_id)
            return ChatResult(
                success=False,
                thread_id=thread_id,
                error_type=ChatErrorType.RESPONSE_PROCESSING_ERROR,
                error_details="Invalid response from AI service",
            )

        messages = result["messages"]
        if not messages:
            logger.error("No messages in response | thread_id: %s", thread_id)
            return ChatResult(
                success=False,
                thread_id=thread_id,
                error_type=ChatErrorType.RESPONSE_PROCESSING_ERROR,
                error_details="No response generated",
            )

        last_message = messages[-1]
        if not hasattr(last_message, "content") or last_message.content is None:
            logger.error("Empty message content | thread_id: %s", thread_id)
            return ChatResult(
                success=False,
                thread_id=thread_id,
                error_type=ChatErrorType.RESPONSE_PROCESSING_ERROR,
                error_details="Empty response generated",
            )

        logger.info(
            "Graph executed successfully | thread_id: %s | AI message preview: %s",
            thread_id,
            last_message.content[:400],
        )

        # TODO: How to handle insert false
        if new_thread:
            title = await generate_chat_title(message, last_message.content)
            res = await app_db.create_user_thread(user_id, thread_id, title, llm)
            if not res:
                logger.error(
                    "Failed to create user thread | user_id: %s | thread_id: %s",
                    user_id,
                    thread_id,
                )
                return ChatResult(
                    success=False,
                    thread_id=thread_id,
                    error_type=ChatErrorType.DATABASE_ERROR,
                    error_details="Failed to save conversation thread",
                )

        save_msgs_res = await _save_msgs_to_db(messages, llm, thread_id, app_db)
        if not save_msgs_res:
            logger.error(
                "Failed to save thread messages | user_id: %s | thread_id: %s",
                user_id,
                thread_id,
            )
            return ChatResult(
                success=False,
                thread_id=thread_id,
                error_type=ChatErrorType.DATABASE_ERROR,
                error_details="Failed to save thread messages",
            )

        tua_res = await app_db.set_thread_updated(user_id, thread_id, llm)
        if not tua_res:
            logger.warning(
                "Thread updated at failure | user_id: %s | thread_id: %s",
                user_id,
                thread_id,
            )

        return ChatResult(
            success=True, message=last_message.content, thread_id=thread_id
        )

    except DatabaseException as e:
        logger.exception("Database exception occured | thread_id: %s", thread_id)
        return ChatResult(
            success=False,
            thread_id=thread_id,
            error_type=ChatErrorType.DATABASE_ERROR,
            error_details="Database exception occured",
        )

    except ValueError as e:
        logger.exception("Value error occured | error: %s", str(e))
        return ChatResult(
            success=False,
            thread_id=thread_id,
            error_type=ChatErrorType.VALIDATION_ERROR,
            error_details=str(e),
        )

    except Exception as e:
        logger.exception(
            "Graph execution failed | thread_id: %s | error: %s", thread_id, str(e)
        )
        return ChatResult(
            success=False,
            thread_id=thread_id,
            error_type=ChatErrorType.RESPONSE_PROCESSING_ERROR,
            error_details="Failed to process AI response",
        )


# NOTE: Was a concern when getting latest index and inserting new message was not atomic.
# Moved everthing into 1 transaction in create_thread_msg. But this may still
# need improvement considerations, possibly when moving to Postgres.
async def _save_msgs_to_db(
    messages: list[BaseMessage], llm: str, thread_id: str, app_db: AppDatabase
) -> bool:
    human_msg = _get_last_human_message(messages)
    ai_msg = _get_last_ai_message(messages)

    if not human_msg or not isinstance(human_msg.id, str):
        raise ValueError("Invalid human message or missing message ID")

    if not ai_msg or not isinstance(ai_msg.id, str):
        raise ValueError("Invalid AI message or missing message ID")

    msg_one_res = await app_db.create_thread_msg(
        get_msg_content_text(human_msg.content),
        MessageType.USER.value,
        llm,
        human_msg.id,
        thread_id,
    )

    msg_two_res = await app_db.create_thread_msg(
        get_msg_content_text(ai_msg.content),
        MessageType.AI.value,
        llm,
        ai_msg.id,
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
    last_msg = messages[-1]
    if isinstance(last_msg, AIMessage):
        return last_msg
    return None
