from fastapi import APIRouter, Depends

from src.controllers import meta_controller
from src.middlewares.rbac import ALL_ROLES, require_roles

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("")
def get_meta(_: dict = Depends(require_roles(*ALL_ROLES))):
    return meta_controller.meta()
