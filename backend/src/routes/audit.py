from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import audit_controller
from src.middlewares.rbac import ADMIN, require_roles

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit(limit: int = 100, db: Session = Depends(get_db),
               _: dict = Depends(require_roles(*ADMIN))):
    return audit_controller.list_audit(db, limit)
