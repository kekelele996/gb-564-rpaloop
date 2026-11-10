from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.constants.enums import ACTIVE_RUN_STATUSES, InterventionStatus, RunStatus
from src.models.intervention import Intervention
from src.models.material import Material
from src.models.process import Process
from src.models.run import Run
from src.models.run_step import RunStep
from src.models.step import Step
from src.services.executor import execute_run_task
from src.services.serializers import intervention_out, run_out
from src.utils.errors import AppError

RESOLVABLE_STATUSES = (InterventionStatus.OPEN.value, InterventionStatus.RETRYING.value)


def _bundle(db, intervention: Intervention) -> dict:
    run = db.get(Run, intervention.run_id)
    process = db.get(Process, run.process_id) if run else None
    material = db.get(Material, run.material_id) if run else None
    run_step = db.get(RunStep, intervention.run_step_id)
    step = db.get(Step, run_step.step_id) if run_step else None
    return intervention_out(intervention, run=run, process=process, material=material,
                            run_step=run_step, step=step)


def list_interventions(db, status: str | None = None, reason: str | None = None,
                       limit: int = 100) -> list[dict]:
    query = select(Intervention).order_by(Intervention.id.desc()).limit(limit)
    if status:
        query = query.where(Intervention.status == status)
    if reason:
        query = query.where(Intervention.reason == reason)
    return [_bundle(db, item) for item in db.scalars(query).all()]


def resolve(db, actor, intervention_id: int, action: str, resolution: str = "") -> dict:
    intervention = db.get(Intervention, intervention_id)
    if intervention is None:
        raise AppError(404, "INTERVENTION_NOT_FOUND", f"接管工单 {intervention_id} 不存在")
    if intervention.status not in RESOLVABLE_STATUSES:
        raise AppError(409, "INTERVENTION_CLOSED", f"工单 {intervention.code} 已处理（{intervention.status}）")
    run = db.get(Run, intervention.run_id)
    if run is None:
        raise AppError(404, "RUN_NOT_FOUND", "关联运行不存在")

    intervention.action = action
    intervention.resolution = resolution or {
        "retry": "人工核验材料后重试", "skip": "本步骤人工跳过", "relocate": "调整定位器后重试",
        "abort": "终止本次运行",
    }[action]
    intervention.resolved_by = actor["email"]
    intervention.resolved_at = datetime.now()

    if action == "abort":
        intervention.status = InterventionStatus.ABORTED.value
        run.status = RunStatus.CANCELLED.value
        run.ended_at = datetime.now()
        run.active_lock = None
        db.commit()
        return {"intervention": _bundle(db, intervention), "run": run_out(run), "resumed": False}

    intervention.status = (
        InterventionStatus.SKIPPED.value if action == "skip" else InterventionStatus.RESOLVED.value
    )
    if intervention.status == InterventionStatus.RESOLVED.value:
        intervention.resolved_at = datetime.now()
    run.status = RunStatus.QUEUED.value
    if not run.active_lock:
        active = db.scalars(
            select(Run).where(Run.material_id == run.material_id,
                              Run.status.in_(ACTIVE_RUN_STATUSES),
                              Run.id != run.id)
        ).first()
        if active:
            raise AppError(409, "E_CONCURRENCY_CONFLICT",
                           f"该公司仍有进行中的运行 {active.run_code}，无法恢复")
        run.active_lock = str(run.material_id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "E_CONCURRENCY_CONFLICT", "同一材料并发冲突，无法恢复运行") from None

    run_id = run.id
    try:
        execute_run_task.delay(run_id)
    except Exception as exc:  # noqa: BLE001
        from src.config.logging import logger
        logger.warning("resume enqueue failed run_id=%s: %s", run_id, exc)
    db.refresh(run)
    return {"intervention": _bundle(db, intervention), "run": run_out(run), "resumed": True}
