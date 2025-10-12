from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from .dependencies import get_app_db, get_current_user
from ..models.request_models import LoginRequest, RegisterRequest
from ..models.user import User
from ..controllers.auth import (
    AuthResult,
    AuthErrorType,
    register_controller,
    login_controller,
)
from ..core.logging import get_logger
from ..core.db_ops.app_db import AppDatabase

logger = get_logger(__name__)
router = APIRouter()


@router.post("/register")
async def register(req: RegisterRequest, app_db: AppDatabase = Depends(get_app_db)):
    result = await register_controller(req.email, req.password, app_db)

    if result.success:
        return JSONResponse(
            status_code=200, content={"success": True, "message": "User registered"}
        )
    else:
        return _create_error_response(result)


@router.post("/login")
async def login(req: LoginRequest, app_db: AppDatabase = Depends(get_app_db)):
    result, token = await login_controller(req.email, req.password, app_db)

    if result.success and token is not None:
        return JSONResponse(
            status_code=200,
            content={
                "token": token.token,
                "token_type": token.token_type,
            },
        )
    else:
        return _create_error_response(result)


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return JSONResponse(
        status_code=200, content={"user_id": user.id, "email": user.email}
    )


def _create_error_response(result: AuthResult) -> JSONResponse:
    """
    Maps ChatResult error types to HTTP status codes and returns formatted error response.
    """
    status_code_map = {
        AuthErrorType.AUTHORIZATION_ERROR: 401,
        AuthErrorType.DATABASE_ERROR: 500,
        AuthErrorType.SYSTEM_ERROR: 500,
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
