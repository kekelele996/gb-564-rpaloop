from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import board_controller
from src.middlewares.rbac import ALL_ROLES, require_roles

router = APIRouter(prefix="/board", tags=["board"])


@router.get("")
def get_board(db: Session = Depends(get_db), _: dict = Depends(require_roles(*ALL_ROLES))):
    return board_controller.get_board(db)
