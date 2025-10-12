import uuid
from typing import Optional, Union
from enum import Enum
from pydantic import BaseModel

from ..core.logging import get_logger
from ..core.db_ops.app_db import AppDatabase
from ..core.auth.password import hash_password, verify_password
from ..core.auth.token import encode_token

logger = get_logger(__name__)


class AuthErrorType(Enum):
    AUTHORIZATION_ERROR = "authorization_error"
    DATABASE_ERROR = "database_error"
    SYSTEM_ERROR = "system_error"


class Token(BaseModel):
    token: str
    token_type: str


class AuthResult:
    def __init__(
        self,
        success: bool,
        error_type: Optional[AuthErrorType] = None,
        error_details: Optional[str] = None,
    ):
        self.success = success
        self.error_type = error_type
        self.error_details = error_details


async def register_controller(
    email: str, password: str, app_db: AppDatabase
) -> AuthResult:

    try:
        if await app_db.user_email_exists(email):
            logger.warning("Cannot register, existing user")
            return AuthResult(
                False, AuthErrorType.AUTHORIZATION_ERROR, "Cannot register user"
            )

        new_user_id = str(uuid.uuid4())
        hsh_pwrd = hash_password(password)
        res = await app_db.create_user(new_user_id, email, hsh_pwrd)

        if not res:
            logger.warning("Database error occured")
            return AuthResult(
                False, AuthErrorType.DATABASE_ERROR, "database access error"
            )

        logger.info("User registered")
        return AuthResult(True)

    except Exception as e:
        logger.exception("System error: %s", str(e))
        return AuthResult(False, AuthErrorType.SYSTEM_ERROR, str(e))


# TODO: Need logging
async def login_controller(
    email: str, password: str, app_db: AppDatabase
) -> tuple[AuthResult, Union[Token, None]]:

    try:
        user = await app_db.get_user_by_email(email)

        if user:
            pword_valid = verify_password(password, user["password"])
        else:
            verify_password(password, "$argon2id$v=19$m=65536,t=3,p=4$dummy")
            pword_valid = False

        if not pword_valid:
            logger.warning("Invalid credentials")
            return (
                AuthResult(
                    False, AuthErrorType.AUTHORIZATION_ERROR, "Invalid credentials"
                ),
                None,
            )

        token = encode_token({"sub": user["id"]})

        return AuthResult(True), Token(token=token, token_type="bearer")

    except Exception as e:
        logger.exception("System error: %s", str(e))
        return AuthResult(False, AuthErrorType.SYSTEM_ERROR, str(e)), None
