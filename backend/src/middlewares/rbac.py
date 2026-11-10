from fastapi import Depends

from src.constants.enums import UserRole
from src.middlewares.auth import get_current_user
from src.utils.errors import AppError

ADMIN = (UserRole.ADMIN.value,)
ADMIN_ENGINEER = (UserRole.ADMIN.value, UserRole.ENGINEER.value)
ALL_ROLES = (UserRole.ADMIN.value, UserRole.ENGINEER.value, UserRole.VIEWER.value)


def require_roles(*roles: str):
    allowed = roles or ALL_ROLES

    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed:
            raise AppError(
                403,
                "FORBIDDEN",
                f"角色 {user['role']} 无权执行该操作（允许：{'/'.join(allowed)}）",
            )
        return user

    return checker
