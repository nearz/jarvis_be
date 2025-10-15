from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from .dependencies import get_current_user, get_app_db
from ..controllers.history import history_controller, HistoryErrorType, HistoryResult
from ..models import User, Thread
from ..models.response_models import HistoryResponse
from ..core.db_ops.app_db import AppDatabase
from ..core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/history")
async def chat(
    user: User = Depends(get_current_user), app_db: AppDatabase = Depends(get_app_db)
):
    logger.info("History request")
    result = await history_controller(user.id, app_db)

    if result.success:
        logger.info("History succesfully fetched")
        if result.threads:
            return HistoryResponse(threads=result.threads)
        else:
            logger.info("No thread history")
            return HistoryResponse(threads=[])
    else:
        logger.warning("History fetch failure")
        return _create_error_response(result)


def _create_error_response(result: HistoryResult) -> JSONResponse:
    """
    Maps ChatResult error types to HTTP status codes and returns formatted error response.
    """
    status_code_map = {
        HistoryErrorType.AUTHORIZATION_ERROR: 401,
        HistoryErrorType.DATABASE_ERROR: 500,
        HistoryErrorType.SYSTEM_ERROR: 500,
    }

    status_code = 400
    if result.error_type is not None:
        status_code = status_code_map.get(result.error_type, 400)

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error_type": result.error_type.value if result.error_type else None,
            "error_details": result.error_details,
        },
    )
