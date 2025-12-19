from fastapi import APIRouter, Depends, HTTPException

from .dependencies import get_current_user
from ..models import User
from ..core.logging import get_logger
from ..controllers.models import supported_models_controller
from ..models.response_models import SupportModelsResponse
from .errors import create_error_response

logger = get_logger(__name__)
router = APIRouter()


@router.get("/models/supported_models")
async def get_supported_models(user: User = Depends(get_current_user)):
    logger.info("Supported models request | user_id: %s", user.id)
    result = await supported_models_controller()
    if not result.success:
        return create_error_response(result)

    return SupportModelsResponse(supported_models=result.supported_models)
