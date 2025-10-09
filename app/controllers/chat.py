from uuid import uuid4
from typing import Union, Optional
from enum import Enum
import logging

from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph, RunnableConfig

from ..agent.state import AgentState, ContextSchema
from ..core.db_ops.agent_checkpoints_db import thread_exists
from ..core.logging import get_logger

logger = get_logger(__name__)


class ChatErrorType(Enum):
    VALIDATION_ERROR = "validation_error"
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
async def chat_controller(
    message: str,
    llm: str,
    graph: CompiledStateGraph[AgentState, ContextSchema, AgentState, AgentState],
    *,
    thread_id: Union[str, None],
) -> ChatResult:
    # New Chat does not provide a thread id, set one for new thread
    if not thread_id:
        thread_id = str(uuid4())
        logger.info("New thread created | thread_id: %s", thread_id)
    else:
        logger.info("Existing thread | thread_id: %s", thread_id)

    # Graph execution
    try:
        msg = HumanMessage(message)
        logger.debug(
            "Invoking graph | thread_id: %s | message preview: %s",
            thread_id,
            message[:100],
        )
        config = RunnableConfig({"configurable": {"thread_id": thread_id}})
        context = ContextSchema(llm)

        coro = graph.ainvoke({"messages": [msg]}, config=config, context=context)
        result = await coro

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
        # This catches LLM API errors, tool errors, graph execution errors
        error_msg = str(e)

        logger.exception(
            "Graph execution failed | thread_id: %s | error message: %s",
            thread_id,
            error_msg,
        )

        return ChatResult(
            success=False,
            thread_id=thread_id,
            error_type=ChatErrorType.GRAPH_EXECUTION_ERROR,
            error_details=error_msg,
        )

    # Process AI Response
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
            "Graph executed succesfully | thread_id: %s | AI message preview: %s",
            thread_id,
            last_message.content[:400],
        )

        return ChatResult(
            success=True, message=last_message.content, thread_id=thread_id
        )

    except Exception as e:
        logger.exception("Graph execution failed | thread_id: %s", thread_id)
        return ChatResult(
            success=False,
            thread_id=thread_id,
            error_type=ChatErrorType.RESPONSE_PROCESSING_ERROR,
            error_details="Failed to process AI response",
        )
