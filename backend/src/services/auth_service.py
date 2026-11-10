from sqlalchemy import select

from src.config.database import SessionLocal
from src.models.user import User
from src.services.serializers import user_out
from src.utils.errors import AppError
from src.utils.security import create_access_token, verify_password


def authenticate(email: str, password: str) -> dict:
    db = SessionLocal()
    try:
        user = db.scalars(select(User).where(User.email == email.lower().strip())).first()
        if user is None or not verify_password(password, user.password_hash):
            raise AppError(401, "AUTH_FAILED", "邮箱或密码不正确")
        if not user.active:
            raise AppError(403, "ACCOUNT_DISABLED", "账号已停用")
        token = create_access_token(subject=user.email, role=user.role,
                                    extra={"uid": user.id, "name": user.name})
        return {"access_token": token, "token_type": "bearer", "user": user_out(user)}
    finally:
        db.close()


def load_user_by_email(email: str) -> dict | None:
    db = SessionLocal()
    try:
        user = db.scalars(select(User).where(User.email == email.lower().strip())).first()
        return user_out(user) if user else None
    finally:
        db.close()
