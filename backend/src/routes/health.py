from fastapi import APIRouter
from sqlalchemy import text

from src.config.database import SessionLocal
from src.config.settings import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    db_status = "up"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as exc:  # noqa: BLE001
        db_status = f"down: {exc}"
    return {
        "status": "ok" if db_status == "up" else "degraded",
        "app": settings.APP_NAME,
        "db": db_status,
        "seed_demo": settings.SEED_DEMO,
    }
