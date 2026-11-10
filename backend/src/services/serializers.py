from datetime import date, datetime


def iso(value: datetime | date | None) -> str | None:
    return value.isoformat() if value else None


def user_out(user) -> dict:
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}


def process_out(process, success_rate: float | None = None) -> dict:
    return {
        "id": process.id,
        "name": process.name,
        "matter_type": process.matter_type,
        "version": process.version,
        "status": process.status,
        "step_count": process.step_count,
        "success_rate": round(success_rate if success_rate is not None else process.success_rate, 4),
        "archived_versions": process.archived_versions or [],
        "owner": process.owner,
        "published_at": iso(process.published_at),
        "created_at": iso(process.created_at),
    }


def step_out(step, include_candidates: bool = True) -> dict:
    data = {
        "id": step.id,
        "process_id": step.process_id,
        "seq": step.seq,
        "action": step.action,
        "target_desc": step.target_desc,
        "timeout_ms": step.timeout_ms,
        "max_retries": step.max_retries,
        "depends_on": step.depends_on or [],
        "assert_rule": step.assert_rule or "",
        "robustness_score": round(float(step.robustness_score or 0), 1),
        "risk_level": step.risk_level,
        "risk_reason": step.risk_reason,
    }
    if include_candidates:
        data["locator_candidates"] = step.locator_candidates or []
        data["locator_scores"] = step.locator_scores or []
    return data


def material_out(material) -> dict:
    return {
        "id": material.id,
        "company_name": material.company_name,
        "credit_code": material.credit_code,
        "contact": material.contact,
        "attachments": material.attachments or [],
        "validity_date": iso(material.validity_date),
        "missing_flags": material.missing_flags or [],
        "credit_valid": bool(material.credit_valid),
        "credit_reason": material.credit_reason,
    }


def run_out(run) -> dict:
    return {
        "id": run.id,
        "run_code": run.run_code,
        "process_id": run.process_id,
        "process_version": run.process_version,
        "material_id": run.material_id,
        "robot_name": run.robot_name,
        "trigger": run.trigger,
        "status": run.status,
        "started_at": iso(run.started_at),
        "ended_at": iso(run.ended_at),
        "total_steps": run.total_steps,
        "success_steps": run.success_steps,
        "retry_count": run.retry_count,
        "attempt_count": run.attempt_count,
        "execution_sequence": run.execution_sequence or [],
        "skipped_steps": run.skipped_steps or [],
        "compensation": run.compensation or [],
        "log_text": run.log_text or "",
        "created_at": iso(run.created_at),
    }


def run_step_out(run_step, step=None) -> dict:
    return {
        "id": run_step.id,
        "run_id": run_step.run_id,
        "step_id": run_step.step_id,
        "seq": run_step.seq,
        "status": run_step.status,
        "locator_used": run_step.locator_used,
        "locator_strategy": run_step.locator_strategy,
        "attempt": run_step.attempt,
        "duration_ms": run_step.duration_ms,
        "error_code": run_step.error_code,
        "error_message": run_step.error_message,
        "idempotency_key": run_step.idempotency_key,
        "output_digest": run_step.output_digest,
        "note": run_step.note,
        "target_desc": step.target_desc if step else "",
        "action": step.action if step else "",
        "assert_rule": (step.assert_rule or "") if step else "",
    }


def intervention_out(intervention, run=None, process=None, material=None, run_step=None, step=None) -> dict:
    return {
        "id": intervention.id,
        "code": intervention.code,
        "run_id": intervention.run_id,
        "run_step_id": intervention.run_step_id,
        "reason": intervention.reason,
        "status": intervention.status,
        "detail": intervention.detail,
        "action": intervention.action,
        "resolution": intervention.resolution,
        "resolved_by": intervention.resolved_by,
        "resolved_at": iso(intervention.resolved_at),
        "created_at": iso(intervention.created_at),
        "run_code": run.run_code if run else "",
        "run_status": run.status if run else "",
        "process_name": process.name if process else "",
        "company_name": material.company_name if material else "",
        "step_seq": (step.seq if step else (run_step.seq if run_step else None)),
        "step_target": step.target_desc if step else "",
    }
