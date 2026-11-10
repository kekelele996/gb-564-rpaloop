import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.config.logging import logger
from src.constants.enums import ACTIVE_RUN_STATUSES, ProcessStatus, RunStatus
from src.models.intervention import Intervention
from src.models.material import Material
from src.models.process import Process
from src.models.run import Run
from src.models.run_step import RunStep
from src.models.step import Step
from src.services.executor import execute_run_task
from src.services.serializers import intervention_out, run_out, run_step_out
from src.utils.errors import AppError


def _new_run_code() -> str:
    return f"RUN-{datetime.now():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"


def _enqueue(run_id: int) -> None:
    try:
        execute_run_task.delay(run_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("enqueue execute_run failed run_id=%s: %s", run_id, exc)


def create_run(db, actor, process_id: int, material_id: int, trigger: str) -> dict:
    process = db.get(Process, process_id)
    if process is None:
        raise AppError(404, "PROCESS_NOT_FOUND", f"流程 {process_id} 不存在")
    material = db.get(Material, material_id)
    if material is None:
        raise AppError(404, "MATERIAL_NOT_FOUND", f"企业材料 {material_id} 不存在")
    dry_run = trigger == "dry_run"
    if not dry_run and process.status != ProcessStatus.PUBLISHED.value:
        raise AppError(422, "PROCESS_NOT_PUBLISHED", "只有已发布流程才能发起正式运行")
    if not dry_run and not material.credit_valid:
        raise AppError(422, "E_CREDIT_INVALID",
                       f"信用代码校验未通过，不能发起申报：{material.credit_reason}")

    db.execute(select(Material).where(Material.id == material_id).with_for_update())
    if not dry_run:
        active = db.scalars(
            select(Run).where(Run.material_id == material_id, Run.status.in_(ACTIVE_RUN_STATUSES))
        ).first()
        if active:
            raise AppError(409, "E_CONCURRENCY_CONFLICT",
                           f"该公司已有进行中的运行 {active.run_code}（同一材料仅允许 1 个并发 run）")

    run = Run(
        run_code=_new_run_code(),
        process_id=process.id,
        process_version=process.version,
        material_id=material.id,
        robot_name="SU-BOT-01",
        trigger=trigger,
        status=RunStatus.QUEUED.value,
        total_steps=process.step_count,
        active_lock=None if dry_run else str(material.id),
    )
    db.add(run)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "E_CONCURRENCY_CONFLICT", "同一材料并发冲突，请稍后重试") from None
    run_id = run.id
    _enqueue(run_id)
    db.refresh(run)
    data = run_out(run)
    data["process_name"] = process.name
    data["company_name"] = material.company_name
    return data


def list_runs(db, status: str | None = None, process_id: int | None = None,
              trigger: str | None = None, limit: int = 50) -> list[dict]:
    query = select(Run).order_by(Run.id.desc()).limit(limit)
    if status:
        query = query.where(Run.status == status)
    if process_id:
        query = query.where(Run.process_id == process_id)
    if trigger:
        query = query.where(Run.trigger == trigger)
    runs = db.scalars(query).all()
    process_map = {p.id: p for p in db.scalars(select(Process)).all()}
    material_map = {m.id: m for m in db.scalars(select(Material)).all()}
    result = []
    for run in runs:
        data = run_out(run)
        data["process_name"] = process_map[run.process_id].name if run.process_id in process_map else ""
        data["company_name"] = material_map[run.material_id].company_name if run.material_id in material_map else ""
        result.append(data)
    return result


def run_entities(db, run_id: int) -> tuple[Run, Process, Material]:
    run = db.get(Run, run_id)
    if run is None:
        raise AppError(404, "RUN_NOT_FOUND", f"运行 {run_id} 不存在")
    process = db.get(Process, run.process_id)
    material = db.get(Material, run.material_id)
    return run, process, material


def run_detail(db, run_id: int) -> dict:
    run, process, material = run_entities(db, run_id)
    run_steps = db.scalars(select(RunStep).where(RunStep.run_id == run_id).order_by(RunStep.seq)).all()
    step_map = {step.id: step for step in db.scalars(
        select(Step).where(Step.process_id == run.process_id)).all()}
    interventions = db.scalars(
        select(Intervention).where(Intervention.run_id == run_id).order_by(Intervention.id)).all()
    data = run_out(run)
    data["process_name"] = process.name if process else ""
    data["matter_type"] = process.matter_type if process else ""
    data["company_name"] = material.company_name if material else ""
    data["credit_code"] = material.credit_code if material else ""
    data["credit_valid"] = bool(material.credit_valid) if material else False
    data["run_steps"] = [run_step_out(item, step_map.get(item.step_id)) for item in run_steps]
    data["interventions"] = [
        intervention_out(item, run=run, process=process, material=material,
                         run_step=next((rs for rs in run_steps if rs.id == item.run_step_id), None),
                         step=next((step_map.get(rs.step_id) for rs in run_steps
                                    if rs.id == item.run_step_id), None))
        for item in interventions
    ]
    return data


def cancel_run(db, actor, run_id: int, note: str = "") -> dict:
    run, _, _ = run_entities(db, run_id)
    if run.status not in ACTIVE_RUN_STATUSES:
        raise AppError(409, "RUN_NOT_ACTIVE", f"运行 {run.run_code} 当前状态 {run.status}，不能取消")
    stamp = datetime.now().strftime("%H:%M:%S")
    run.log_text = ((run.log_text or "") + f"\n[{stamp}] 操作员 {actor['email']} 取消运行：{note}").strip()[-12000:]
    run.status = RunStatus.CANCELLED.value
    run.ended_at = datetime.now()
    run.active_lock = None
    db.commit()
    return run_out(run)
