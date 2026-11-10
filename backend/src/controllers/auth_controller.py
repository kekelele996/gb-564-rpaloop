from src.services import auth_service


def login(payload: dict) -> dict:
    return auth_service.authenticate(payload["email"], payload["password"])


def me(user: dict) -> dict:
    return {"user": user}
