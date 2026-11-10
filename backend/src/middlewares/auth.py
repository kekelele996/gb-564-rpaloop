from fastapi import Header

from src.services.auth_service import load_user_by_email
from src.utils.errors import AppError
from src.utils.security import decode_access_token


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(401, "UNAUTHORIZED", "缺少 Bearer 登录凭证")
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    if not payload:
        raise AppError(401, "TOKEN_INVALID", "登录凭证无效或已过期")
    user = load_user_by_email(payload.get("sub", ""))
    if user is None:
        raise AppError(401, "USER_NOT_FOUND", "登录用户不存在")
    return user


def optional_user(authorization: str | None = Header(default=None)) -> dict | None:
    try:
        return get_current_user(authorization)
    except AppError:
        return None
