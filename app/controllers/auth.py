import uuid
from typing import Optional, Union
from enum import Enum

from ..models import Token
from ..core.logging import get_logger
from ..core.db_ops.app_db import AppDatabase, DatabaseException
from ..core.auth.password import hash_password, verify_password
from ..core.auth.token import encode_token

logger = get_logger(__name__)

DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$Kxe9asgS7lH9J5nM/cofkA$4DmKyLnrHIAMmdIv1uLsFq2wIKojh6kP8r/IkVQ6byw"


class AuthErrorType(Enum):
    AUTHORIZATION_ERROR = "authorization_error"
    DATABASE_ERROR = "database_error"
    SYSTEM_ERROR = "system_error"


class AuthResult:
    def __init__(
        self,
        success: bool,
        token: Optional[Token] = None,
        error_type: Optional[AuthErrorType] = None,
        error_details: Optional[str] = None,
    ):
        self.success = success
        self.token = token
        self.error_type = error_type
        self.error_details = error_details


# NOTE:
# If in production I should fail silently to avoid user enumeration.
# Consider industry patterns like sending an email to complete registration. Or if
# existing user let them know someone tried to register with their email.
async def register_controller(
    email: str, password: str, app_db: AppDatabase
) -> AuthResult:

    try:
        if await app_db.user_email_exists(email):
            logger.warning("Registration failure")
            return AuthResult(
                success=False,
                error_type=AuthErrorType.AUTHORIZATION_ERROR,
                error_details="Cannot register user",
            )

        new_user_id = str(uuid.uuid4())
        hsh_pwrd = hash_password(password)

        res = await app_db.create_user(new_user_id, email, hsh_pwrd)

        if not res:
            logger.warning("Registration failure")
            return AuthResult(
                success=False,
                error_type=AuthErrorType.AUTHORIZATION_ERROR,
                error_details="Cannot register user",
            )

        logger.info("User registered")
        return AuthResult(success=True)

    except DatabaseException as e:
        logger.exception("Database exception occurred")
        return AuthResult(
            success=False,
            error_type=AuthErrorType.DATABASE_ERROR,
            error_details="Database exception occurred",
        )

    except Exception as e:
        logger.exception("System error")
        return AuthResult(
            success=False,
            error_type=AuthErrorType.SYSTEM_ERROR,
            error_details="Unexpected system failure",
        )


async def login_controller(
    email: str, password: str, app_db: AppDatabase
) -> AuthResult:

    try:
        user = await app_db.get_user_by_email(email)

        if user:
            stored_hash = user["password"]
        else:
            stored_hash = DUMMY_HASH

        valid_pwd = verify_password(password, stored_hash)

        if not user or not valid_pwd:
            logger.warning("Invalid credentials")
            return AuthResult(
                success=False,
                error_type=AuthErrorType.AUTHORIZATION_ERROR,
                error_details="Invalid credentials",
            )

        sll_res = await app_db.set_last_login(user["id"])
        if not sll_res:
            logger.warning("Last login write failed | user_id: %s", user["id"])

        logger.info("succesful login: %s", user["id"])
        token = encode_token({"sub": user["id"]})

        return AuthResult(success=True, token=Token(token=token, token_type="bearer"))

    except DatabaseException as e:
        logger.exception("Database exception occurred")
        verify_password(
            password,
            DUMMY_HASH,
        )
        return AuthResult(
            success=False,
            error_type=AuthErrorType.DATABASE_ERROR,
            error_details="Database exception occurred",
        )

    except Exception as e:
        logger.exception("System error")
        return AuthResult(
            success=False,
            error_type=AuthErrorType.SYSTEM_ERROR,
            error_details="unexpected system failure",
        )
