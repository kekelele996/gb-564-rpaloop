from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import material_controller
from src.middlewares.rbac import ADMIN, ALL_ROLES, require_roles
from src.schemas.material import MaterialCreateRequest

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("")
def list_materials(only_invalid: bool = False, db: Session = Depends(get_db),
                   _: dict = Depends(require_roles(*ALL_ROLES))):
    return material_controller.list_materials(db, only_invalid)


@router.post("")
def create_material(payload: MaterialCreateRequest, db: Session = Depends(get_db),
                    _: dict = Depends(require_roles(*ADMIN))):
    return material_controller.create_material(db, payload.model_dump())


@router.get("/{material_id}/credit-check")
def validate_material(material_id: int, db: Session = Depends(get_db),
                      _: dict = Depends(require_roles(*ALL_ROLES))):
    return material_controller.validate_material(db, material_id)
