from src.config.database import SessionLocal
from src.models.audit_log import AuditLog


def write_audit(actor_email: str, actor_role: str, action: str, resource: str = "",
                resource_id: str = "", method: str = "", path: str = "",
                status_code: int = 0, detail: str = "") -> None:
    db = SessionLocal()
    try:
        db.add(AuditLog(
            actor_email=actor_email or "anonymous",
            actor_role=actor_role or "",
            action=action,
            resource=resource,
            resource_id=str(resource_id or ""),
            method=method,
            path=path,
            status_code=status_code,
            detail=detail[:4000],
        ))
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
    finally:
        db.close()


def list_audit(db, limit: int = 100) -> list[dict]:
    from sqlalchemy import select
    rows = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)).all()
    return [
        {
            "id": row.id,
            "actor_email": row.actor_email,
            "actor_role": row.actor_role,
            "action": row.action,
            "resource": row.resource,
            "resource_id": row.resource_id,
            "method": row.method,
            "path": row.path,
            "status_code": row.status_code,
            "detail": row.detail,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
