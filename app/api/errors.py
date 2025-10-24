from fastapi.responses import JSONResponse

from ..models.controller_models import BaseResult, ErrorType
from ..core.logging import get_logger

logger = get_logger(__name__)


def create_error_response(result: BaseResult) -> JSONResponse:
    """
    Maps ChatResult error types to HTTP status codes and returns formatted error response.
    """
    status_code_map = {
        ErrorType.AUTHORIZATION_ERROR: 401,
        ErrorType.VALIDATION_ERROR: 400,
        ErrorType.FORBIDDEN_ERROR: 403,
        ErrorType.DATABASE_ERROR: 503,
        ErrorType.GRAPH_EXECUTION_ERROR: 502,
        ErrorType.LLM_ERROR: 502,
        ErrorType.LLM_RESPONSE_PROCESSING_ERROR: 502,
        ErrorType.SYSTEM_ERROR: 500,
    }

    error_type_value = result.error_type.value if result.error_type else ""
    status_code = (
        status_code_map.get(result.error_type, 400) if result.error_type else 400
    )

    logger.warning(
        "Controller result error | error_type: %s | error_details: %s | controller result type: %s",
        error_type_value,
        result.error_details,
        type(result),
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error_type": error_type_value,
            "error_details": result.error_details,
        },
    )
