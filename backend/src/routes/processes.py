from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import process_controller
from src.middlewares.rbac import ADMIN, ADMIN_ENGINEER, ALL_ROLES, require_roles
from src.schemas.process import ProcessActionRequest, StepImportRequest, StepUpdateRequest
from src.schemas.run import RunCreateRequest

router = APIRouter(prefix="/processes", tags=["processes"])


@router.get("")
def list_processes(status: str | None = None, matter_type: str | None = None,
                   db: Session = Depends(get_db), _: dict = Depends(require_roles(*ALL_ROLES))):
    return process_controller.list_processes(db, status, matter_type)


@router.get("/{process_id}")
def get_process(process_id: int, db: Session = Depends(get_db),
                _: dict = Depends(require_roles(*ALL_ROLES))):
    return process_controller.get_process(db, process_id)


@router.put("/{process_id}/steps/{step_id}")
def update_step(process_id: int, step_id: int, payload: StepUpdateRequest,
                db: Session = Depends(get_db), _: dict = Depends(require_roles(*ADMIN_ENGINEER))):
    return process_controller.update_step(db, process_id, step_id, payload.model_dump(exclude_unset=True))


@router.post("/{process_id}/rescore")
def rescore(process_id: int, db: Session = Depends(get_db),
            _: dict = Depends(require_roles(*ADMIN_ENGINEER))):
    return process_controller.rescore(db, process_id)


@router.post("/{process_id}/publish")
def publish(process_id: int, payload: ProcessActionRequest | None = None,
            db: Session = Depends(get_db), _: dict = Depends(require_roles(*ADMIN))):
    return process_controller.publish(db, process_id, (payload.note if payload else ""))


@router.post("/{process_id}/archive")
def archive(process_id: int, payload: ProcessActionRequest | None = None,
            db: Session = Depends(get_db), _: dict = Depends(require_roles(*ADMIN))):
    return process_controller.archive(db, process_id, (payload.note if payload else ""))


@router.post("/{process_id}/import")
def import_steps(process_id: int, payload: StepImportRequest, db: Session = Depends(get_db),
                 _: dict = Depends(require_roles(*ADMIN_ENGINEER))):
    return process_controller.import_steps(db, process_id, payload.steps, payload.replace)


@router.post("/{process_id}/dry-run")
def dry_run(process_id: int, payload: RunCreateRequest, db: Session = Depends(get_db),
            user: dict = Depends(require_roles(*ADMIN_ENGINEER))):
    return process_controller.dry_run(db, user, process_id, payload.material_id)
