from uuid import uuid4
from typing import Union, Optional
from enum import Enum
import logging

from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph, RunnableConfig

from ..agent.state import AgentState, ContextSchema


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


# TODO: Remove pretty_print to logging
# TODO: Is there a better way to setup ainvoke params package? Maybe a func in state.
async def chat_controller(
    message: str,
    llm: str,
    graph: CompiledStateGraph[AgentState, ContextSchema, AgentState, AgentState],
    *,
    thread_id: Union[str, None],
) -> ChatResult:
    try:
        # New Chat does not provide a thread id
        if not thread_id:
            thread_id = str(uuid4())

        # Type check params
        if not isinstance(message, str):
            return ChatResult(
                success=False,
                error_type=ChatErrorType.VALIDATION_ERROR,
                error_details="Message must be a string",
            )

        if not isinstance(llm, str):
            return ChatResult(
                success=False,
                error_type=ChatErrorType.VALIDATION_ERROR,
                error_details="LLM model must be a string",
            )

        if not isinstance(thread_id, str):
            return ChatResult(
                success=False,
                error_type=ChatErrorType.VALIDATION_ERROR,
                error_details="Thread ID must be a string",
            )

        # Content validation
        if not message.strip():
            return ChatResult(
                success=False,
                error_type=ChatErrorType.VALIDATION_ERROR,
                error_details="Message cannot be empty",
            )

        if not llm.strip():
            return ChatResult(
                success=False,
                error_type=ChatErrorType.VALIDATION_ERROR,
                error_details="LLM model must be specified",
            )

        if not thread_id.strip():
            return ChatResult(
                success=False,
                error_type=ChatErrorType.VALIDATION_ERROR,
                error_details="Thread ID must be specified",
            )

    except Exception as e:
        logging.error(f"Unexpected error during validation: {e}")
        return ChatResult(
            success=False,
            error_type=ChatErrorType.SYSTEM_ERROR,
            error_details="An unexpected system error occurred",
        )

    # Graph execution
    try:
        msg = HumanMessage(message)
        msg.pretty_print()
        config = RunnableConfig({"configurable": {"thread_id": thread_id}})
        context = ContextSchema(llm)

        coro = graph.ainvoke({"messages": [msg]}, config=config, context=context)
        result = await coro

    except TimeoutError as e:
        return ChatResult(
            success=False,
            thread_id=thread_id,
            error_type=ChatErrorType.GRAPH_EXECUTION_ERROR,
            error_details="Request timed out. Please try again.",
        )

    except Exception as e:
        # This catches LLM API errors, tool errors, graph execution errors
        error_msg = str(e)

        return ChatResult(
            success=False,
            thread_id=thread_id,
            error_type=ChatErrorType.GRAPH_EXECUTION_ERROR,
            error_details=error_msg,
        )

    # Process AI Response
    try:
        if not result or "messages" not in result:
            return ChatResult(
                success=False,
                thread_id=thread_id,
                error_type=ChatErrorType.RESPONSE_PROCESSING_ERROR,
                error_details="Invalid response from AI service",
            )

        messages = result["messages"]
        if not messages:
            return ChatResult(
                success=False,
                thread_id=thread_id,
                error_type=ChatErrorType.RESPONSE_PROCESSING_ERROR,
                error_details="No response generated",
            )

        last_message = messages[-1]
        if not hasattr(last_message, "content") or last_message.content is None:
            return ChatResult(
                success=False,
                thread_id=thread_id,
                error_type=ChatErrorType.RESPONSE_PROCESSING_ERROR,
                error_details="Empty response generated",
            )

        return ChatResult(
            success=True, message=last_message.content, thread_id=thread_id
        )

    except Exception as e:
        return ChatResult(
            success=False,
            thread_id=thread_id,
            error_type=ChatErrorType.RESPONSE_PROCESSING_ERROR,
            error_details="Failed to process AI response",
        )
