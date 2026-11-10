from datetime import datetime

from sqlalchemy import func, select

from src.constants.enums import ACTIVE_RUN_STATUSES, MatterType, ProcessStatus, RiskLevel, StepAction
from src.constants.limits import MAX_STEPS_PER_PROCESS
from src.models.process import Process
from src.models.run import Run
from src.models.run_step import RunStep
from src.models.step import Step
from src.services.executor import load_history
from src.services.locator_score import score_step
from src.services.serializers import iso, process_out, step_out
from src.utils.errors import AppError


def success_rate_map(db) -> dict[int, float]:
    rows = db.execute(
        select(Run.process_id, Run.status, func.count(Run.id))
        .where(Run.trigger != "dry_run")
        .group_by(Run.process_id, Run.status)
    ).all()
    totals: dict[int, int] = {}
    succeeded: dict[int, int] = {}
    for process_id, status, count in rows:
        totals[process_id] = totals.get(process_id, 0) + count
        if status == "succeeded":
            succeeded[process_id] = succeeded.get(process_id, 0) + count
    return {pid: (succeeded.get(pid, 0) / total if total else 0.0) for pid, total in totals.items()}


def list_processes(db, status: str | None = None, matter_type: str | None = None) -> list[dict]:
    query = select(Process).order_by(Process.id)
    if status:
        query = query.where(Process.status == status)
    if matter_type:
        query = query.where(Process.matter_type == matter_type)
    processes = db.scalars(query).all()
    rates = success_rate_map(db)
    return [process_out(process, rates.get(process.id, process.success_rate)) for process in processes]


def get_process(db, process_id: int) -> Process:
    process = db.get(Process, process_id)
    if process is None:
        raise AppError(404, "PROCESS_NOT_FOUND", f"流程 {process_id} 不存在")
    return process


def process_detail(db, process_id: int) -> dict:
    process = get_process(db, process_id)
    steps = db.scalars(select(Step).where(Step.process_id == process_id).order_by(Step.seq)).all()
    data = process_out(process, success_rate_map(db).get(process.id, process.success_rate))
    data["steps"] = [step_out(step) for step in steps]
    data["risk_summary"] = {
        "high": sum(1 for step in steps if step.risk_level == RiskLevel.HIGH.value),
        "medium": sum(1 for step in steps if step.risk_level == RiskLevel.MEDIUM.value),
        "low": sum(1 for step in steps if step.risk_level == RiskLevel.LOW.value),
    }
    return data


def build_step_scores(db, step: Step) -> dict:
    history = load_history(db, step.id)
    return score_step({
        "id": step.id,
        "seq": step.seq,
        "target_desc": step.target_desc,
        "locator_candidates": step.locator_candidates or [],
    }, history)


def rescore_process(db, process_id: int) -> dict:
    process = get_process(db, process_id)
    steps = db.scalars(select(Step).where(Step.process_id == process_id).order_by(Step.seq)).all()
    results = []
    for step in steps:
        result = build_step_scores(db, step)
        step.locator_scores = result["candidates"]
        step.robustness_score = float(result["robustness_score"])
        step.risk_level = result["risk_level"]
        step.risk_reason = result["risk_reason"]
        results.append(result)
    process.step_count = len(steps)
    db.commit()
    return {
        "process_id": process.id,
        "process_name": process.name,
        "steps": results,
        "high_risk_steps": [item["seq"] for item in results if item["risk_level"] == "high"],
    }


def update_step(db, process_id: int, step_id: int, payload: dict) -> dict:
    process = get_process(db, process_id)
    step = db.get(Step, step_id)
    if step is None or step.process_id != process_id:
        raise AppError(404, "STEP_NOT_FOUND", f"步骤 {step_id} 不属于流程 {process_id}")
    if process.status == ProcessStatus.ARCHIVED.value:
        raise AppError(409, "PROCESS_ARCHIVED", "已归档流程不允许编辑")
    if payload.get("action") is not None:
        if payload["action"] not in [item.value for item in StepAction]:
            raise AppError(422, "INVALID_ACTION", f"不支持的步骤动作：{payload['action']}")
        step.action = payload["action"]
    if payload.get("target_desc") is not None:
        step.target_desc = payload["target_desc"][:255]
    if payload.get("locator_candidates") is not None:
        candidates = [dict(item) for item in payload["locator_candidates"]][:6]
        if not candidates:
            raise AppError(422, "LOCATOR_REQUIRED", "至少保留一个定位器候选")
        step.locator_candidates = candidates
    if payload.get("timeout_ms") is not None:
        step.timeout_ms = int(payload["timeout_ms"])
    if payload.get("max_retries") is not None:
        step.max_retries = int(payload["max_retries"])
    if payload.get("assert_rule") is not None:
        step.assert_rule = payload["assert_rule"] or None
    if payload.get("depends_on") is not None:
        step.depends_on = sorted({int(item) for item in payload["depends_on"] if int(item) != step.seq})
    db.flush()
    result = build_step_scores(db, step)
    step.locator_scores = result["candidates"]
    step.robustness_score = float(result["robustness_score"])
    step.risk_level = result["risk_level"]
    step.risk_reason = result["risk_reason"]
    db.commit()
    return {"step": step_out(step), "score": result, "process_id": process_id}


def import_steps(db, process_id: int, steps: list[dict], replace: bool = False) -> dict:
    process = get_process(db, process_id)
    if process.status == ProcessStatus.ARCHIVED.value:
        raise AppError(409, "PROCESS_ARCHIVED", "已归档流程不允许导入录制步骤")
    if not steps:
        raise AppError(422, "EMPTY_RECORDING", "录制 JSON 中没有步骤")
    if len(steps) > MAX_STEPS_PER_PROCESS:
        raise AppError(422, "TOO_MANY_STEPS", f"步骤数超过上限 {MAX_STEPS_PER_PROCESS}")
    if replace:
        db.query(Step).filter(Step.process_id == process_id).delete()
        db.flush()
        base_seq = 0
    else:
        current = db.scalars(select(Step).where(Step.process_id == process_id)).all()
        base_seq = max((step.seq for step in current), default=0)
    created = []
    for index, raw in enumerate(steps, start=1):
        action = raw.get("action", "click")
        if action not in [item.value for item in StepAction]:
            raise AppError(422, "INVALID_ACTION", f"第 {index} 步动作不支持：{action}")
        candidates = raw.get("locator_candidates") or raw.get("locators") or []
        if not candidates:
            candidates = [{"strategy": "css", "selector": f"#recorded-step-{base_seq + index}",
                           "desc": "录制导入默认定位器"}]
        step = Step(
            process_id=process_id,
            seq=base_seq + index,
            action=action,
            target_desc=str(raw.get("target_desc") or raw.get("target") or f"录制步骤 {index}")[:255],
            locator_candidates=[dict(item) for item in candidates][:6],
            timeout_ms=int(raw.get("timeout_ms", 15000)),
            max_retries=int(raw.get("max_retries", 2)),
            depends_on=[int(item) for item in raw.get("depends_on", [])],
            assert_rule=raw.get("assert_rule") or None,
            locator_scores=[],
            risk_level="medium",
            risk_reason="no_history",
        )
        db.add(step)
        created.append(step)
    db.flush()
    rescore_process(db, process_id)
    process = get_process(db, process_id)
    process.step_count = db.scalar(select(func.count(Step.id)).where(Step.process_id == process_id))
    db.commit()
    return {"process_id": process_id, "imported": len(created), "step_count": process.step_count}


def publish_process(db, process_id: int, note: str = "") -> dict:
    process = get_process(db, process_id)
    if process.status == ProcessStatus.ARCHIVED.value:
        raise AppError(409, "PROCESS_ARCHIVED", "已归档流程不能发布，请先恢复或新建版本")
    step_count = db.scalar(select(func.count(Step.id)).where(Step.process_id == process_id))
    if not step_count:
        raise AppError(422, "EMPTY_PROCESS", "流程没有步骤，不能发布")
    archived = list(process.archived_versions or [])
    if process.status == ProcessStatus.PUBLISHED.value:
        archived.append(f"v{process.version}")
        process.version = process.version + 1
    process.status = ProcessStatus.PUBLISHED.value
    process.archived_versions = archived[-10:]
    process.step_count = int(step_count)
    process.published_at = datetime.now()
    if note:
        process.owner = process.owner
    db.commit()
    return {"process": process_out(process), "note": note}


def archive_process(db, process_id: int, note: str = "") -> dict:
    process = get_process(db, process_id)
    if process.status == ProcessStatus.ARCHIVED.value:
        return {"process": process_out(process), "note": note}
    process.status = ProcessStatus.ARCHIVED.value
    db.commit()
    return {"process": process_out(process), "note": note}


def step_for_run(db, message: str) -> None:
    raise AppError(422, "INVALID_STEP", message)
