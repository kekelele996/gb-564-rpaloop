from fastapi import Response

from src.services import report_service, run_service


def create_run(db, user, payload: dict) -> dict:
    return run_service.create_run(db, user, payload["process_id"], payload["material_id"], payload["trigger"])


def list_runs(db, status=None, process_id=None, trigger=None, limit: int = 50) -> dict:
    items = run_service.list_runs(db, status, process_id, trigger, limit)
    return {"total": len(items), "items": items}


def get_run(db, run_id: int) -> dict:
    return run_service.run_detail(db, run_id)


def cancel_run(db, user, run_id: int, note: str = "") -> dict:
    return run_service.cancel_run(db, user, run_id, note)


def export_report(db, run_id: int, fmt: str) -> Response:
    if fmt == "csv":
        content, filename = report_service.report_csv(db, run_id)
        media_type = "text/csv; charset=utf-8"
    else:
        content, filename = report_service.report_markdown(db, run_id)
        media_type = "text/markdown; charset=utf-8"
    return Response(
        content=content.encode("utf-8"),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
