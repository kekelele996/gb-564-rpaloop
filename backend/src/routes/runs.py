from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import run_controller
from src.middlewares.rbac import ADMIN_ENGINEER, ALL_ROLES, require_roles
from src.schemas.run import RunCancelRequest, RunCreateRequest

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("")
def create_run(payload: RunCreateRequest, db: Session = Depends(get_db),
               user: dict = Depends(require_roles(*ADMIN_ENGINEER))):
    return run_controller.create_run(db, user, payload.model_dump())


@router.get("")
def list_runs(status: str | None = None, process_id: int | None = None,
              trigger: str | None = None, limit: int = 50, db: Session = Depends(get_db),
              _: dict = Depends(require_roles(*ALL_ROLES))):
    return run_controller.list_runs(db, status, process_id, trigger, limit)


@router.get("/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db),
            _: dict = Depends(require_roles(*ALL_ROLES))):
    return run_controller.get_run(db, run_id)


@router.post("/{run_id}/cancel")
def cancel_run(run_id: int, payload: RunCancelRequest | None = None, db: Session = Depends(get_db),
               user: dict = Depends(require_roles(*ADMIN_ENGINEER))):
    return run_controller.cancel_run(db, user, run_id, (payload.note if payload else ""))


@router.get("/{run_id}/report")
def export_report(run_id: int, format: str = "markdown", db: Session = Depends(get_db),
                  _: dict = Depends(require_roles(*ALL_ROLES))):
    fmt = "csv" if format.lower() == "csv" else "markdown"
    return run_controller.export_report(db, run_id, fmt)
