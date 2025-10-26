from uuid import UUID
from fastapi import Request, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..core.db_ops.app_db import AppDatabase, DatabaseException
from ..core.auth.token import decode_token
from ..core.logging import get_logger
from ..models import User

security = HTTPBearer()
logger = get_logger(__name__)


def get_app_graph(req: Request):
    return req.app.state.graph


def get_graph_saver(req: Request):
    return req.app.state.saver


def get_app_db(req: Request):
    return req.app.state.app_db


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
    app_db: AppDatabase = Depends(get_app_db),
) -> User:
    """
    Validates JWT and returns current user.
    Raises:
        HTTPException 401: If token invalid, expired, or user not found.
    """
    logger.info("Authorizing user")
    token = creds.credentials

    try:
        payload = decode_token(token)

    except HTTPException as e:
        logger.error("Authorization error | error: %s", e.detail)
        raise

    except Exception as e:
        logger.exception("Unexpected system error occurred")
        raise HTTPException(
            status_code=500,
            detail="Unexpected system error",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")

    if not user_id:
        logger.warning("Token missing user identifier")
        raise HTTPException(
            status_code=401,
            detail="Token missing user identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = await app_db.get_user_by_id(user_id)
    except DatabaseException as e:
        logger.error("Database exception occurred | error: %s", str(e))
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user:
        logger.warning("Could not fetch user")
        raise HTTPException(
            status_code=401,
            detail="Authentication Error",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info("User authorized | user_id: %s", user["id"])
    return User(id=user["id"], email=user["email"])


async def thread_validation(
    thread_id: str,
    app_db: AppDatabase = Depends(get_app_db),
    user=Depends(get_current_user),
) -> str:
    thread_id = thread_id.strip()
    logger.info("Validating thread | thread_id: %s | user_id: %s", thread_id, user.id)
    try:
        UUID(thread_id)
        thread_does_exist = await app_db.thread_exists(thread_id)
        thread_owned = await app_db.verify_thread_ownership(user.id, thread_id)

    except ValueError:
        logger.warning(
            "Invalid thread_id format | thread_id: %s | user_id: %s", thread_id, user.id
        )
        raise HTTPException(status_code=400, detail="Invalid thread_id format")

    except DatabaseException as e:
        logger.error("Database exception occurred | error: %s", str(e))
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable",
        )

    except Exception as e:
        logger.exception(
            "Exception occurred while validating thread | thread_id: %s | error: %s",
            thread_id,
            str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="Unexpected system error",
        )

    if not thread_does_exist:
        logger.warning(
            "Thread does not exist | thread_id: %s | user_id: %s",
            thread_id,
            user.id,
        )
        raise HTTPException(status_code=404, detail="Thread does not exist")

    if not thread_owned:
        logger.warning(
            "Thread is not owned by user | thread_id: %s | user_id: %s",
            thread_id,
            user.id,
        )
        raise HTTPException(status_code=403, detail="User cannot access thread")

    logger.info("Thread validated | thread_id: %s | user_id: %s", thread_id, user.id)
    return thread_id
