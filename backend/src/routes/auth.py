from fastapi import APIRouter, Depends

from src.controllers import auth_controller
from src.middlewares.auth import get_current_user
from src.schemas.auth import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    return auth_controller.login(payload.model_dump())


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return auth_controller.me(user)
