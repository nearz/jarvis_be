from fastapi import APIRouter, Depends

from .dependencies import get_app_db, get_current_user
from ..models.request_models import LoginRequest, RegisterRequest
from ..models.response_models import RegisterResponse, TokenResponse, UserResponse
from ..models import User
from ..controllers.auth import register_controller, login_controller
from ..core.logging import get_logger
from ..core.db_ops.app_db import AppDatabase
from .errors import create_error_response

logger = get_logger(__name__)
router = APIRouter()


@router.post("/register", response_model=RegisterResponse)
async def register(req: RegisterRequest, app_db: AppDatabase = Depends(get_app_db)):
    logger.info("Register request submitted")
    result = await register_controller(req.email, req.password, app_db)

    if not result.success:
        logger.warning("Registration failed")
        return create_error_response(result)

    logger.info("User successfully registered")
    return RegisterResponse()


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, app_db: AppDatabase = Depends(get_app_db)):
    logger.info("Login request")
    result = await login_controller(req.email, req.password, app_db)

    if not result.success or result.token is None:
        logger.warning("Login failed")
        return create_error_response(result)

    logger.info("Login successful")
    return TokenResponse(token=result.token.token, token_type=result.token.token_type)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return UserResponse(id=user.id, email=user.email)
