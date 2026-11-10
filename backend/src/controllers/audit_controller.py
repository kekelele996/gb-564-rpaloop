from src.services import audit_service


def list_audit(db, limit: int = 100) -> dict:
    items = audit_service.list_audit(db, limit)
    return {"total": len(items), "items": items}
