from fastapi import Request, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..core.db_ops.app_db import AppDatabase, DatabaseException
from ..core.auth.token import decode_token
from ..models import User

security = HTTPBearer()


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
    token = creds.credentials

    try:
        payload = decode_token(token)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Unexpected error during authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Token missing user identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = await app_db.get_user_by_id(user_id)
    except DatabaseException as e:
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication Error",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return User(id=user["id"], email=user["email"])
