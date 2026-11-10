from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import intervention_controller
from src.middlewares.rbac import ADMIN_ENGINEER, ALL_ROLES, require_roles
from src.schemas.intervention import InterventionResolveRequest

router = APIRouter(prefix="/interventions", tags=["interventions"])


@router.get("")
def list_interventions(status: str | None = None, reason: str | None = None,
                       db: Session = Depends(get_db), _: dict = Depends(require_roles(*ALL_ROLES))):
    return intervention_controller.list_interventions(db, status, reason)


@router.post("/{intervention_id}/resolve")
def resolve(intervention_id: int, payload: InterventionResolveRequest,
            db: Session = Depends(get_db), user: dict = Depends(require_roles(*ADMIN_ENGINEER))):
    return intervention_controller.resolve(db, user, intervention_id, payload.model_dump())
