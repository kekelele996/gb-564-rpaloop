from src.services import board_service


def get_board(db) -> dict:
    return board_service.board_snapshot(db)
