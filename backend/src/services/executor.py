"""算法 B：步骤 DAG 调度 + 断点续跑 / 失败接管。

- 步骤依赖 depends_on 组成 DAG（为空表示链式依赖 seq-1），Kahn 拓扑排序得到执行序列；
- 幂等键 idempotency_key = sha256(run_id + step_id + material.credit_code)，
  续跑时已成功且幂等键一致的步骤直接跳过（skipped_steps 落库）；
- 失败分类：transient(timeout/network) → 指数退避 1/2/4s 至 max_retries；
  assert_failed / locator_drift → 生成 Intervention 并把 run 挂起为 takeover；
- 并发：同一 Material 同时仅允许 1 个进行中的 run（runs.active_lock 唯一约束 + 行锁）。
- 可复现：dry_run 不真实等待；assert 失败由 Material.missing_flags 固定触发。
"""
import hashlib
import time
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.config.database import SessionLocal
from src.config.celery_app import celery_app
from src.config.logging import logger
from src.config.settings import settings
from src.constants.enums import ErrorCode, InterventionReason, InterventionStatus, RunStatus, RunStepStatus
from src.models.intervention import Intervention
from src.models.material import Material
from src.models.process import Process
from src.models.run import Run
from src.models.run_step import RunStep
from src.models.step import Step

ATTEMPT_RETRY_BASE_SECONDS = 1


class StepResult:
    def __init__(self, status: str, error_code: str | None = None, message: str = "",
                 locator_used: str = "", locator_strategy: str = "", attempt: int = 1,
                 output_digest: str = "", duration_ms: int = 0):
        self.status = status
        self.error_code = error_code
        self.message = message
        self.locator_used = locator_used
        self.locator_strategy = locator_strategy
        self.attempt = attempt
        self.output_digest = output_digest
        self.duration_ms = duration_ms


def idempotency_key(run_id: int, step_id: int, credit_code: str) -> str:
    payload = f"{run_id}:{step_id}:{(credit_code or '').strip().upper()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def kahn_topological_order(steps: list[Step]) -> list[Step]:
    if not steps:
        return []
    by_seq = {step.seq: step for step in steps}
    first_seq = min(by_seq)
    indegree = {seq: 0 for seq in by_seq}
    children: dict[int, list[int]] = {seq: [] for seq in by_seq}
    for step in steps:
        deps = list(step.depends_on or [])
        if not deps and step.seq != first_seq:
            deps = [step.seq - 1]
        for dep in deps:
            if dep not in by_seq or dep == step.seq:
                continue
            indegree[step.seq] += 1
            children[dep].append(step.seq)
    ready = sorted(seq for seq, deg in indegree.items() if deg == 0)
    order: list[int] = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for child in sorted(children[current]):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort()
    if len(order) != len(by_seq):
        raise ValueError("step dependency graph contains a cycle")
    return [by_seq[seq] for seq in order]


def choose_locator(step: Step) -> tuple[dict, list[dict]]:
    candidates = list(step.locator_candidates or [])
    if not candidates:
        return {"strategy": "css", "selector": f"#step-{step.seq}"}, []
    return candidates[0], candidates[1:]


def _simulate_locator_miss(step: Step, candidate: dict, key: str) -> bool:
    """主定位器含动态片段时，约 40% 概率首次未命中，改用备选（确定性哈希，可复现）。"""
    selector = str(candidate.get("selector", ""))
    risky = any(pattern in selector for pattern in ("20250318", "build", "uuid"))
    if not risky:
        return False
    digest = hashlib.sha256(f"{key}:locator".encode()).hexdigest()
    return int(digest[:2], 16) % 10 < 4


def evaluate_assert(step: Step, material: Material) -> tuple[bool, str]:
    rule = (step.assert_rule or "").strip()
    if not rule:
        return True, ""
    if rule == "credit_code_valid":
        if not material.credit_valid:
            return False, f"统一社会信用代码校验失败：{material.credit_reason}"
        return True, ""
    if rule.startswith("attachment:"):
        name = rule.split(":", 1)[1].split(" ")[0].strip()
        if f"attachment:{name}" in (material.missing_flags or []):
            return False, f"材料缺失：{name} 未上传（missing_flags 标记）"
        return True, ""
    if rule in ("receipt_generated", "accepted_no_generated"):
        return True, ""
    return True, ""


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def execute_step_once(step: Step, material: Material, key: str, dry_run: bool) -> StepResult:
    candidate, backups = choose_locator(step)
    missed = _simulate_locator_miss(step, candidate, key)
    chosen = backups[0] if (missed and backups) else candidate
    attempt = 2 if missed else 1
    duration_ms = 0 if dry_run else 8 + int(_digest(key)[:2], 16) % 32
    if not dry_run:
        time.sleep(duration_ms / 1000.0)

    flags = material.missing_flags or []
    if f"timeout_seq:{step.seq}" in flags:
        return StepResult("transient", ErrorCode.E_TIMEOUT.value, "政务网响应超时",
                          chosen["selector"], chosen.get("strategy", "css"), attempt, "", duration_ms)

    if step.action == "input" and "信用代码" in (step.target_desc or "") and not material.credit_valid:
        return StepResult("assert_failed", ErrorCode.E_CREDIT_INVALID.value,
                          f"信用代码非法：{material.credit_reason}",
                          chosen["selector"], chosen.get("strategy", "css"), attempt, "", duration_ms)

    ok, message = evaluate_assert(step, material)
    if not ok:
        return StepResult("assert_failed", ErrorCode.E_ASSERT_FAILED.value, message,
                          chosen["selector"], chosen.get("strategy", "css"), attempt, "", duration_ms)

    return StepResult("ok", None, message, chosen["selector"], chosen.get("strategy", "css"),
                      attempt, _digest(f"{key}:{chosen['selector']}"), duration_ms)


def _append_log(run: Run, line: str) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    existing = run.log_text or ""
    run.log_text = (existing + f"\n[{stamp}] {line}").strip()[-12000:]


def _get_or_create_runstep(db, run: Run, step: Step, key: str) -> RunStep:
    run_step = db.scalars(
        select(RunStep).where(RunStep.run_id == run.id, RunStep.step_id == step.id)
    ).first()
    if run_step is None:
        run_step = RunStep(run_id=run.id, step_id=step.id, seq=step.seq, status="running",
                           idempotency_key=key)
        db.add(run_step)
        db.flush()
    return run_step


def _open_intervention(db, run: Run, run_step: RunStep, reason: str, detail: str) -> Intervention:
    code = f"IV-{run.run_code}-{run_step.seq:02d}"
    existing = db.scalars(select(Intervention).where(Intervention.code == code)).first()
    if existing:
        existing.status = InterventionStatus.OPEN.value
        existing.reason = reason
        existing.detail = detail
        existing.action = ""
        existing.resolution = ""
        existing.resolved_by = None
        existing.resolved_at = None
        return existing
    intervention = Intervention(
        code=code, run_id=run.id, run_step_id=run_step.id, reason=reason,
        status=InterventionStatus.OPEN.value, detail=detail,
    )
    db.add(intervention)
    db.flush()
    return intervention


def load_history(db, step_id: int, limit: int = 8) -> list[dict]:
    rows = db.scalars(
        select(RunStep).where(RunStep.step_id == step_id).order_by(RunStep.updated_at.desc()).limit(limit)
    ).all()
    return [
        {"locator_used": row.locator_used, "attempt": row.attempt, "status": row.status}
        for row in rows
    ]


def _finish(db, run: Run, status: str) -> None:
    run.status = status
    run.ended_at = datetime.now()
    if status != RunStatus.TAKEOVER.value:
        run.active_lock = None
    db.commit()


def _execute(db, run: Run, dry_run: bool) -> None:
    process = db.get(Process, run.process_id)
    material = db.get(Material, run.material_id)
    if process is None or material is None:
        run.log_text = (run.log_text or "") + "\n[error] 流程或材料不存在，终止运行"
        _finish(db, run, RunStatus.FAILED.value)
        return

    steps = db.scalars(select(Step).where(Step.process_id == run.process_id).order_by(Step.seq)).all()
    try:
        ordered = kahn_topological_order(list(steps))
    except ValueError as exc:
        _append_log(run, f"调度失败：{exc}")
        _finish(db, run, RunStatus.FAILED.value)
        return

    run.execution_sequence = [step.seq for step in ordered]
    run.total_steps = len(ordered)
    run.status = RunStatus.RUNNING.value
    run.started_at = run.started_at or datetime.now()
    run.attempt_count = (run.attempt_count or 0) + 1
    _append_log(run, f"robot={run.robot_name} 触发={run.trigger} DAG 拓扑序列={run.execution_sequence}")
    db.commit()

    interventions = db.scalars(select(Intervention).where(Intervention.run_id == run.id)).all()
    resolved_actions: dict[int, str] = {}
    for item in interventions:
        if item.status in (InterventionStatus.RESOLVED.value, InterventionStatus.SKIPPED.value):
            resolved_actions[item.run_step_id] = item.action or item.status

    existing_steps = {rs.step_id: rs for rs in db.scalars(
        select(RunStep).where(RunStep.run_id == run.id)).all()}

    skipped: list[int] = []
    retries_used = 0
    success = 0

    for step in ordered:
        db.refresh(run)
        if run.status == RunStatus.CANCELLED.value:
            _append_log(run, "运行被操作员取消")
            return

        key = idempotency_key(run.id, step.id, material.credit_code)
        run_step = existing_steps.get(step.id)
        manual_action = resolved_actions.get(run_step.id) if run_step else None

        if (run_step and run_step.status in (RunStepStatus.OK.value, RunStepStatus.RETRIED.value)
                and run_step.idempotency_key == key):
            skipped.append(step.seq)
            success += 1
            _append_log(run, f"step {step.seq:02d} 幂等键命中，跳过（断点续跑）")
            continue

        if run_step and manual_action == "skip":
            run_step.status = RunStepStatus.SKIPPED.value
            run_step.note = "接管跳过"
            skipped.append(step.seq)
            _append_log(run, f"step {step.seq:02d} 接管选择跳过")
            db.commit()
            continue

        if run_step and manual_action in ("retry", "relocate") and run_step.status == RunStepStatus.FAILED.value:
            run_step.status = RunStepStatus.OK.value
            run_step.attempt = int(run_step.attempt or 1) + 1
            run_step.error_code = None
            run_step.error_message = ""
            run_step.note = "人工接管放行（材料已补录 / 定位器已调整）"
            retries_used += 1
            success += 1
            _append_log(run, f"step {step.seq:02d} 接管 {manual_action} 后放行")
            db.commit()
            continue

        result = execute_step_once(step, material, key, dry_run)
        attempt = result.attempt
        while result.status == "transient" and attempt <= step.max_retries and not dry_run:
            wait_seconds = ATTEMPT_RETRY_BASE_SECONDS * (2 ** (attempt - 1))
            _append_log(run, f"step {step.seq:02d} transient {result.error_code}，"
                             f"{wait_seconds}s 后第 {attempt + 1} 次重试")
            time.sleep(wait_seconds)
            attempt += 1
            retries_used += 1
            result = execute_step_once(step, material, key, dry_run)
            if result.status == "ok":
                result.attempt = attempt

        run_step = _get_or_create_runstep(db, run, step, key)
        run_step.seq = step.seq
        run_step.attempt = attempt
        run_step.duration_ms = result.duration_ms
        run_step.locator_used = result.locator_used
        run_step.locator_strategy = result.locator_strategy
        run_step.output_digest = result.output_digest
        run_step.error_code = result.error_code
        run_step.error_message = result.message

        if result.status == "ok":
            run_step.status = RunStepStatus.RETRIED.value if attempt > 1 else RunStepStatus.OK.value
            success += 1
            _append_log(run, f"step {step.seq:02d} {step.action} {step.target_desc} "
                             f"attempt={attempt} locator={result.locator_used}")
            db.commit()
            continue

        run_step.status = RunStepStatus.FAILED.value
        reason = InterventionReason.ASSERT_FAILED.value if result.status == "assert_failed" else InterventionReason.TIMEOUT.value
        _open_intervention(db, run, run_step, reason, result.message or result.error_code or "步骤失败")
        _append_log(run, f"step {step.seq:02d} 失败 {result.error_code}：{result.message}，生成接管工单")
        run.success_steps = success
        run.retry_count = (run.retry_count or 0) + retries_used
        _finish(db, run, RunStatus.TAKEOVER.value)
        return

    run.success_steps = success
    run.retry_count = (run.retry_count or 0) + retries_used
    run.skipped_steps = skipped
    _append_log(run, f"运行完成：成功 {success}/{run.total_steps}，跳过 {len(skipped)}，重试 {retries_used}")
    _finish(db, run, RunStatus.SUCCEEDED.value)


@celery_app.task(name="rpaloop.execute_run", bind=True, max_retries=0)
def execute_run_task(self, run_id: int) -> dict:
    logger.info("execute_run start run_id=%s", run_id)
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if run is None:
            return {"run_id": run_id, "result": "not_found"}
        if run.status in (RunStatus.SUCCEEDED.value, RunStatus.CANCELLED.value):
            return {"run_id": run_id, "result": "ignored", "status": run.status}
        _execute(db, run, dry_run=(run.trigger == "dry_run"))
        db.refresh(run)
        return {"run_id": run_id, "result": row_status(run)}
    except IntegrityError as exc:
        db.rollback()
        logger.warning("execute_run integrity error run_id=%s: %s", run_id, exc)
        return {"run_id": run_id, "result": "conflict"}
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.exception("execute_run failed run_id=%s", run_id)
        try:
            run = db.get(Run, run_id)
            if run:
                _append_log(run, f"执行器异常：{exc}")
                _finish(db, run, RunStatus.FAILED.value)
        except Exception:  # noqa: BLE001
            pass
        return {"run_id": run_id, "result": "error", "error": str(exc)}
    finally:
        db.close()


def row_status(run: Run) -> str:
    return run.status
