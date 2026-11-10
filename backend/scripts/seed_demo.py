"""seed 演示数据（幂等）：苏城企服政务材料录入 RPA 录制回放台。

自然键 upsert：users.email / processes.name / steps(process_id,seq) /
materials.company_name / runs.run_code / run_steps(run_id,step_id) / interventions.code。
重复执行只补齐缺失行，不新增、不覆盖用户修改；算法派生字段（定位器稳健分、
信用代码校验结果、流程成功率）每次按 seed 历史确定性重算。
"""
from datetime import date, datetime
from hashlib import sha256

from sqlalchemy import select

from src.config.database import Base, SessionLocal, engine
from src.models.intervention import Intervention
from src.models.material import Material
from src.models.process import Process
from src.models.run import Run
from src.models.run_step import RunStep
from src.models.step import Step
from src.models.user import User
from src.services.executor import idempotency_key
from src.services.locator_score import score_step
from src.utils.credit_code import validate_credit_code
from src.utils.security import hash_password

PASSWORD = "Demo@2026"

USERS = [
    {"email": "admin@rpaloop.io", "name": "顾承宇", "role": "admin"},
    {"email": "engineer@rpaloop.io", "name": "陆嘉禾", "role": "engineer"},
    {"email": "viewer@rpaloop.io", "name": "闻人静", "role": "viewer"},
]


def cand(strategy: str, selector: str, desc: str) -> dict:
    return {"strategy": strategy, "selector": selector, "desc": desc}


def annual_steps() -> list[dict]:
    return [
        {"seq": 1, "action": "click", "target_desc": "打开政务服务网企业年报入口",
         "candidates": [cand("id", "#annual-entry-card", "年报入口卡片"),
                        cand("text", "//a[normalize-space()='企业年报']", "按菜单文本定位")]},
        {"seq": 2, "action": "input", "target_desc": "录入统一社会信用代码",
         "candidates": [cand("css", 'div.form-shell > div:nth-child(3) > input[id="creditCode-20250318"]',
                             "旧版信用代码输入框（含构建时间戳）"),
                        cand("text", "//label[normalize-space()='统一社会信用代码']/following::input[1]",
                             "按中文标签文本定位"),
                        cand("id", "#annual-form-credit-input", "新版信用代码输入框 id")]},
        {"seq": 3, "action": "assert", "target_desc": "信用代码校验通过", "assert_rule": "credit_code_valid",
         "candidates": [cand("id", "#credit-verify-badge", "校验结果徽标"),
                        cand("css", "#annual-form .verify-badge", "校验徽标样式")]},
        {"seq": 4, "action": "input", "target_desc": "录入企业名称",
         "candidates": [cand("css", "#annual-form .field-company input", "企业名称输入框"),
                        cand("text", "//label[normalize-space()='企业名称']/following::input[1]", "标签文本定位")]},
        {"seq": 5, "action": "upload", "target_desc": "上传营业执照扫描件",
         "candidates": [cand("css", "#annual-form .upload-license input[type=file]", "营业执照上传控件"),
                        cand("role", "button[name='上传营业执照']", "按钮无障碍名称")]},
        {"seq": 6, "action": "assert", "target_desc": "校验审计报告附件", "assert_rule": "attachment:审计报告 exists",
         "candidates": [cand("text", "//h4[contains(text(),'审计报告')]", "附件事项标题"),
                        cand("css", "#annual-form .attachment-audit", "审计报告附件区")]},
        {"seq": 7, "action": "input", "target_desc": "录入注册资本（万元）",
         "candidates": [cand("css", "#annual-form .field-capital input", "注册资本输入框"),
                        cand("text", "//label[normalize-space()='注册资本（万元）']/following::input[1]", "标签文本定位")]},
        {"seq": 8, "action": "click", "target_desc": "提交年报申报",
         "candidates": [cand("text", "//button[normalize-space()='提交年报']", "提交按钮文本"),
                        cand("css", "#annual-form .btn-submit", "提交按钮样式")]},
        {"seq": 9, "action": "assert", "target_desc": "校验申报回执编号", "assert_rule": "receipt_generated",
         "candidates": [cand("id", "#receipt-code", "回执编号文本")]},
    ]


def qualification_steps() -> list[dict]:
    rows = [
        ("click", "打开高企资质申报入口", "#qualification-entry-link", "资质入口链接"),
        ("input", "录入统一社会信用代码", "#qual-form .field-credit input", "信用代码输入框"),
        ("input", "录入企业名称", "#qual-form .field-company input", "企业名称输入框"),
        ("upload", "上传高新技术企业证书", "#qual-form .upload-cert input[type=file]", "证书上传控件"),
        ("assert", "校验高新技术企业证书", "#qual-cert-badge", "证书校验徽标"),
        ("input", "录入研发投入（万元）", "#qual-form .field-rd input", "研发投入输入框"),
        ("assert", "校验提交回执", "#qual-receipt", "回执编号"),
    ]
    steps = []
    for index, (action, desc, selector, label) in enumerate(rows, start=1):
        step = {"seq": index, "action": action, "target_desc": desc,
                "candidates": [cand("css", selector, label),
                               cand("text", f"//label[normalize-space()='{desc[-6:]}']", "按标签文本定位")]}
        if index == 5:
            step["assert_rule"] = "attachment:高新技术企业证书 exists"
        if index == 7:
            step["assert_rule"] = "receipt_generated"
        steps.append(step)
    return steps


def subsidy_steps() -> list[dict]:
    rows = [
        ("click", "打开稳岗补贴申报入口", "#subsidy-entry-link", "补贴入口链接", None),
        ("input", "录入统一社会信用代码", "#subsidy-form .field-credit input", "信用代码输入框", None),
        ("input", "录入企业名称", "#subsidy-form .field-company input", "企业名称输入框", None),
        ("input", "录入参保人数", "#subsidy-form .field-headcount input", "参保人数输入框", None),
        ("upload", "上传营业执照", "#subsidy-form .upload-license input[type=file]", "营业执照上传控件", None),
        ("assert", "校验审计报告附件", "//h4[contains(text(),'审计报告')]", "审计报告标题", "attachment:审计报告 exists"),
        ("input", "录入银行账号", "#subsidy-form .field-bank input", "银行账号输入框", None),
        ("click", "提交稳岗补贴申报", "#subsidy-submit", "提交按钮", None),
    ]
    steps = []
    for index, (action, desc, selector, label, rule) in enumerate(rows, start=1):
        item = {"seq": index, "action": action, "target_desc": desc,
                "candidates": [cand("text" if selector.startswith("//") else "css", selector, label),
                               cand("css", f"#subsidy-form .step-{index:02d}", "表单步骤容器（旧版）")]}
        if rule:
            item["assert_rule"] = rule
        steps.append(item)
    return steps


def change_steps() -> list[dict]:
    rows = [
        ("click", "打开工商变更登记入口", "#change-entry-link", "变更入口链接", None),
        ("input", "录入统一社会信用代码", "#change-form .field-credit input", "信用代码输入框", None),
        ("input", "录入变更事项", "#change-form .field-item input", "变更事项输入框", None),
        ("upload", "上传股东会决议", "#change-form .upload-resolution input[type=file]", "决议上传控件", None),
        ("assert", "校验股东会决议盖章", "//h4[contains(text(),'股东会决议')]", "决议标题", "attachment:股东会决议 exists"),
        ("input", "录入新法定代表人", "#change-form .field-legal input", "法定代表人输入框", None),
        ("click", "提交变更登记", "#change-submit", "提交按钮", None),
        ("assert", "校验受理编号", "#accept-no", "受理编号", "accepted_no_generated"),
    ]
    steps = []
    for index, (action, desc, selector, label, rule) in enumerate(rows, start=1):
        item = {"seq": index, "action": action, "target_desc": desc,
                "candidates": [cand("text" if selector.startswith("//") else "css", selector, label),
                               cand("css", f"#change-form .step-{index:02d}", "表单步骤容器（旧版）")]}
        if rule:
            item["assert_rule"] = rule
        steps.append(item)
    return steps


PROCESS_SPECS = [
    {"name": "2025 企业年报", "matter_type": "annual_report", "status": "published", "version": 2,
     "archived_versions": ["v1"], "owner": "苏城企服 RPA 组（年报线）", "steps": annual_steps()},
    {"name": "高新技术企业资质认定", "matter_type": "qualification", "status": "published", "version": 3,
     "archived_versions": ["v1", "v2"], "owner": "苏城企服 RPA 组（资质线）", "steps": qualification_steps()},
    {"name": "稳岗返还补贴申报", "matter_type": "subsidy", "status": "published", "version": 1,
     "archived_versions": [], "owner": "苏城企服 RPA 组（补贴线）", "steps": subsidy_steps()},
    {"name": "工商变更登记", "matter_type": "change", "status": "draft", "version": 1,
     "archived_versions": [], "owner": "苏城企服 RPA 组（变更线）", "steps": change_steps()},
]

MATERIALS = [
    {"company_name": "苏州恒瑞精密机械有限公司", "credit_code": "91320500MA1XY2K3AJ",
     "contact": "陈立群 0512-6688-1201",
     "attachments": ["营业执照", "2024年度财务报表", "公司章程"], "validity_date": date(2027, 3, 31),
     "missing_flags": []},
    {"company_name": "苏州云启智能装备有限公司", "credit_code": "91320594MA2ABCD5TK",
     "contact": "王雪梅 0512-6720-8834",
     "attachments": ["营业执照", "高新技术企业证书", "2024年度审计报告"], "validity_date": date(2026, 12, 31),
     "missing_flags": []},
    {"company_name": "苏城智造科技（苏州）有限公司", "credit_code": "91320505MA3EFGH7UY",
     "contact": "顾明远 0512-6581-2290",
     "attachments": ["营业执照", "2024年度财务报表"], "validity_date": date(2026, 6, 30),
     "missing_flags": ["attachment:审计报告"]},
    {"company_name": "苏州新纶纺织股份有限公司", "credit_code": "91320500MA4JKLM9WY",
     "contact": "沈佩兰 0512-6338-7712",
     "attachments": ["营业执照", "2024年度审计报告", "社保参保花名册"], "validity_date": date(2027, 1, 15),
     "missing_flags": []},
    {"company_name": "苏州华泰针织有限公司", "credit_code": "91320507MA5MNPQ1X0",
     "contact": "周阿根 0512-6543-9087",
     "attachments": ["营业执照"], "validity_date": date(2026, 9, 30), "missing_flags": []},
    {"company_name": "苏州信德模塑有限公司", "credit_code": "91320508MA6QRTU3Y3",
     "contact": "李志强 0512-6611-4432",
     "attachments": ["营业执照", "公司章程"], "validity_date": date(2026, 8, 31), "missing_flags": []},
]

# step tuple: (seq, status, attempt, candidate_index, error_code, note)
RUN_SPECS = [
    {"code": "RUN-20261103-001", "process": "2025 企业年报", "material": "苏州恒瑞精密机械有限公司",
     "trigger": "schedule", "status": "succeeded", "robot": "SU-BOT-01",
     "start": datetime(2026, 11, 3, 9, 12, 4), "end": datetime(2026, 11, 3, 9, 13, 41),
     "attempt_count": 1, "retry_count": 1,
     "steps": [(1, "ok", 1, 0, None, ""), (2, "retried", 2, 0, None, "旧版动态定位器首次未命中，改用标签定位"),
               (3, "ok", 1, 0, None, ""), (4, "ok", 1, 0, None, ""), (5, "ok", 1, 0, None, ""),
               (6, "ok", 1, 0, None, ""), (7, "ok", 1, 0, None, ""), (8, "ok", 1, 0, None, ""),
               (9, "ok", 1, 0, None, "")]},
    {"code": "RUN-20261103-002", "process": "高新技术企业资质认定", "material": "苏州云启智能装备有限公司",
     "trigger": "schedule", "status": "succeeded", "robot": "SU-BOT-02",
     "start": datetime(2026, 11, 3, 14, 2, 10), "end": datetime(2026, 11, 3, 14, 3, 25),
     "attempt_count": 1, "retry_count": 0,
     "steps": [(1, "ok", 1, 0, None, ""), (2, "ok", 1, 0, None, ""), (3, "ok", 1, 0, None, ""),
               (4, "ok", 1, 0, None, ""), (5, "ok", 1, 0, None, ""), (6, "ok", 1, 0, None, ""),
               (7, "ok", 1, 0, None, "")]},
    {"code": "RUN-20261104-001", "process": "稳岗返还补贴申报", "material": "苏州华泰针织有限公司",
     "trigger": "schedule", "status": "failed", "robot": "SU-BOT-01",
     "start": datetime(2026, 11, 4, 10, 21, 3), "end": datetime(2026, 11, 4, 10, 24, 18),
     "attempt_count": 1, "retry_count": 2,
     "steps": [(1, "ok", 1, 0, None, ""),
               (2, "failed", 3, 0, "E_TIMEOUT", "政务网在信用代码校验环节连续超时，重试 3 次失败")]},
    {"code": "RUN-20261104-002", "process": "高新技术企业资质认定", "material": "苏州恒瑞精密机械有限公司",
     "trigger": "schedule", "status": "succeeded", "robot": "SU-BOT-02",
     "start": datetime(2026, 11, 4, 15, 40, 6), "end": datetime(2026, 11, 4, 15, 41, 30),
     "attempt_count": 1, "retry_count": 1,
     "steps": [(1, "ok", 1, 0, None, ""), (2, "ok", 1, 0, None, ""), (3, "ok", 1, 0, None, ""),
               (4, "ok", 1, 0, None, ""), (5, "ok", 1, 0, None, ""), (6, "retried", 2, 0, None, "研发投入输入框首次超时，重试后成功"),
               (7, "ok", 1, 0, None, "")]},
    {"code": "RUN-20261105-001", "process": "稳岗返还补贴申报", "material": "苏城智造科技（苏州）有限公司",
     "trigger": "manual", "status": "succeeded", "robot": "SU-BOT-01",
     "start": datetime(2026, 11, 5, 9, 5, 12), "end": datetime(2026, 11, 5, 9, 31, 40),
     "attempt_count": 2, "retry_count": 1,
     "steps": [(1, "ok", 1, 0, None, ""), (2, "ok", 1, 0, None, ""), (3, "ok", 1, 0, None, ""),
               (4, "ok", 1, 0, None, ""), (5, "ok", 1, 0, None, ""),
               (6, "ok", 2, 0, None, "接管 manual 放行：人工核验审计报告扫描件"),
               (7, "ok", 1, 0, None, ""), (8, "ok", 1, 0, None, "")]},
    {"code": "RUN-20261106-001", "process": "高新技术企业资质认定", "material": "苏州新纶纺织股份有限公司",
     "trigger": "schedule", "status": "succeeded", "robot": "SU-BOT-02",
     "start": datetime(2026, 11, 6, 9, 44, 2), "end": datetime(2026, 11, 6, 9, 49, 51),
     "attempt_count": 2, "retry_count": 1,
     "steps": [(1, "ok", 1, 0, None, ""), (2, "ok", 1, 0, None, ""), (3, "ok", 1, 0, None, ""),
               (4, "ok", 2, 1, None, "接管 relocate 放行：改用证书列表文本定位器"),
               (5, "ok", 1, 0, None, ""), (6, "ok", 1, 0, None, ""), (7, "ok", 1, 0, None, "")]},
    {"code": "RUN-20261108-001", "process": "2025 企业年报", "material": "苏州新纶纺织股份有限公司",
     "trigger": "schedule", "status": "failed", "robot": "SU-BOT-01",
     "start": datetime(2026, 11, 8, 22, 0, 5), "end": datetime(2026, 11, 8, 22, 6, 30),
     "attempt_count": 1, "retry_count": 2,
     "steps": [(1, "ok", 1, 0, None, ""),
               (2, "retried", 2, 1, None, "旧版动态定位器未命中，改用标签定位"),
               (3, "failed", 3, 0, "E_TIMEOUT", "信用代码校验徽标长时间未返回，重试 3 次超时")]},
    {"code": "RUN-20261110-001", "process": "2025 企业年报", "material": "苏州云启智能装备有限公司",
     "trigger": "schedule", "status": "running", "robot": "SU-BOT-02",
     "start": datetime(2026, 11, 10, 8, 30, 0), "end": None,
     "attempt_count": 1, "retry_count": 1,
     "steps": [(1, "ok", 1, 0, None, ""),
               (2, "retried", 2, 1, None, "旧版动态定位器未命中，改用标签定位")]},
]

INTERVENTION_SPECS = [
    {"run_code": "RUN-20261106-001", "seq": 4, "reason": "locator_drift", "status": "resolved",
     "action": "relocate", "detail": "高新证书上传控件改版，旧 css 定位失效",
     "resolution": "改用证书列表 aria 文本定位器，重试后通过", "resolved_by": "engineer@rpaloop.io",
     "resolved_at": datetime(2026, 11, 6, 9, 48, 20)},
    {"run_code": "RUN-20261105-001", "seq": 6, "reason": "manual", "status": "resolved",
     "action": "retry", "detail": "审计报告附件断言拦截，企业当日补传扫描件",
     "resolution": "人工核验补传的审计报告扫描件齐全后放行", "resolved_by": "engineer@rpaloop.io",
     "resolved_at": datetime(2026, 11, 5, 9, 30, 12)},
    {"run_code": "RUN-20261108-001", "seq": 3, "reason": "timeout", "status": "open",
     "action": "", "detail": "信用代码校验徽标 3 次重试均超时，等待人工确认政务网状态",
     "resolution": "", "resolved_by": None, "resolved_at": None},
]


def get_or_create(db, model, defaults: dict, **keys):
    instance = db.scalars(select(model).filter_by(**keys)).first()
    if instance:
        return instance, False
    instance = model(**{**keys, **defaults})
    db.add(instance)
    db.flush()
    return instance, True


def seed() -> dict:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for spec in USERS:
            get_or_create(db, User, {"name": spec["name"], "role": spec["role"],
                                     "password_hash": hash_password(PASSWORD), "active": True},
                          email=spec["email"])
        db.commit()

        processes: dict[str, Process] = {}
        for spec in PROCESS_SPECS:
            process, _ = get_or_create(
                db, Process,
                {"matter_type": spec["matter_type"], "status": spec["status"], "version": spec["version"],
                 "archived_versions": spec["archived_versions"], "owner": spec["owner"],
                 "step_count": len(spec["steps"]),
                 "published_at": spec.get("published_at", datetime(2026, 10, 28, 16, 0, 0)
                                          if spec["status"] == "published" else None)},
                name=spec["name"])
            processes[process.name] = process
            for step_spec in spec["steps"]:
                get_or_create(
                    db, Step,
                    {"action": step_spec["action"], "target_desc": step_spec["target_desc"],
                     "locator_candidates": step_spec["candidates"], "locator_scores": [],
                     "timeout_ms": 15000, "max_retries": 2, "depends_on": [],
                     "assert_rule": step_spec.get("assert_rule"), "risk_level": "medium",
                     "risk_reason": "no_history", "robustness_score": 50.0},
                    process_id=process.id, seq=step_spec["seq"])
        db.commit()

        materials: dict[str, Material] = {}
        for spec in MATERIALS:
            valid, reason = validate_credit_code(spec["credit_code"])
            material, _ = get_or_create(
                db, Material,
                {"credit_code": spec["credit_code"], "contact": spec["contact"],
                 "attachments": spec["attachments"], "validity_date": spec["validity_date"],
                 "missing_flags": spec["missing_flags"], "credit_valid": valid,
                 "credit_reason": reason},
                company_name=spec["company_name"])
            material.credit_valid = valid
            material.credit_reason = reason
            materials[material.company_name] = material
        db.commit()

        step_index = {(step.process_id, step.seq): step for step in db.scalars(select(Step)).all()}
        for spec in RUN_SPECS:
            process = processes[spec["process"]]
            material = materials[spec["material"]]
            run, _ = get_or_create(
                db, Run,
                {"process_id": process.id, "process_version": process.version,
                 "material_id": material.id, "robot_name": spec["robot"], "trigger": spec["trigger"],
                 "status": spec["status"], "started_at": spec["start"], "ended_at": spec["end"],
                 "total_steps": len(process.steps) if hasattr(process, "steps") else process.step_count,
                 "success_steps": sum(1 for s in spec["steps"] if s[1] in ("ok", "retried")),
                 "retry_count": spec["retry_count"], "attempt_count": spec["attempt_count"],
                 "execution_sequence": [s[0] for s in spec["steps"]],
                 "skipped_steps": [], "compensation": [], "log_text": "",
                 "active_lock": str(material.id) if spec["status"] == "running" else None},
                run_code=spec["code"])
            run.total_steps = process.step_count
            if spec["status"] == "running":
                run.active_lock = str(material.id)
            for (seq, status, attempt, cand_index, error_code, note) in spec["steps"]:
                step = step_index[(process.id, seq)]
                candidates = step.locator_candidates or []
                locator = candidates[cand_index] if len(candidates) > cand_index else candidates[0]
                key = idempotency_key(run.id, step.id, material.credit_code)
                digest = sha256(f"{run.run_code}:{seq}".encode()).hexdigest() if status in ("ok", "retried") else ""
                run_step, created = get_or_create(
                    db, RunStep,
                    {"seq": seq, "status": status, "locator_used": locator["selector"],
                     "locator_strategy": locator.get("strategy", "css"), "attempt": attempt,
                     "duration_ms": 14 + (seq * 7 + attempt * 3) % 28, "error_code": error_code,
                     "error_message": note if error_code else "", "idempotency_key": key,
                     "output_digest": digest, "note": note},
                    run_id=run.id, step_id=step.id)
                if created:
                    db.flush()
                else:
                    run_step.status = status
                    run_step.note = note
            # 运行日志（可重复执行，内容固定）
            lines = [f"robot={spec['robot']} 触发={spec['trigger']} 流程={process.name} v{run.process_version}",
                     f"企业={material.company_name} 信用代码={material.credit_code}",
                     f"DAG 拓扑序列={[s[0] for s in spec['steps']]}"]
            lines += [f"step {seq:02d} 接管放行 {note}" if note and status == "ok" and attempt > 1
                      else f"step {seq:02d} {status}" + (f" {error_code}" if error_code else "")
                      for (seq, status, attempt, _c, error_code, note) in spec["steps"]]
            run.log_text = "[" + spec["start"].strftime("%H:%M:%S") + "] " + "\n[seed] ".join(lines)
        db.commit()

        run_map = {run.run_code: run for run in db.scalars(select(Run)).all()}
        for spec in INTERVENTION_SPECS:
            run = run_map[spec["run_code"]]
            run_step = db.scalars(select(RunStep).where(
                RunStep.run_id == run.id, RunStep.seq == spec["seq"])).first()
            if run_step is None:
                continue
            get_or_create(
                db, Intervention,
                {"run_id": run.id, "run_step_id": run_step.id,
                 "reason": spec["reason"], "status": spec["status"], "detail": spec["detail"],
                 "action": spec["action"], "resolution": spec["resolution"],
                 "resolved_by": spec["resolved_by"], "resolved_at": spec["resolved_at"]},
                code=f"IV-{run.run_code}-{spec['seq']:02d}")
        db.commit()

        # 派生数据：信用代码校验、定位器稳健性评分、流程成功率（确定性重算）
        for material in db.scalars(select(Material)).all():
            valid, reason = validate_credit_code(material.credit_code)
            material.credit_valid = valid
            material.credit_reason = reason
        db.commit()

        for process in db.scalars(select(Process)).all():
            steps = db.scalars(select(Step).where(Step.process_id == process.id).order_by(Step.seq)).all()
            run_rows = db.scalars(select(Run).where(Run.process_id == process.id,
                                                   Run.trigger != "dry_run")).all()
            for step in steps:
                history = [
                    {"locator_used": rs.locator_used, "attempt": rs.attempt, "status": rs.status}
                    for rs in db.scalars(select(RunStep).where(RunStep.step_id == step.id)
                                         .order_by(RunStep.updated_at.desc()).limit(8)).all()
                ]
                result = score_step({"id": step.id, "seq": step.seq,
                                     "target_desc": step.target_desc,
                                     "locator_candidates": step.locator_candidates or []}, history)
                step.locator_scores = result["candidates"]
                step.robustness_score = float(result["robustness_score"])
                step.risk_level = result["risk_level"]
                step.risk_reason = result["risk_reason"]
            process.step_count = len(steps)
            total = len(run_rows)
            process.success_rate = round(sum(1 for run in run_rows if run.status == "succeeded") / total, 4) if total else 0.0
        db.commit()

        counts = {
            "processes": len(db.scalars(select(Process)).all()),
            "steps": len(db.scalars(select(Step)).all()),
            "materials": len(db.scalars(select(Material)).all()),
            "runs": len(db.scalars(select(Run)).all()),
            "runsteps": len(db.scalars(select(RunStep)).all()),
            "interventions": len(db.scalars(select(Intervention)).all()),
            "users": len(db.scalars(select(User)).all()),
        }
        print("SEED_DEMO ready brand=rpaloop demo_accounts=admin/engineer/viewer")
        print(
            "SEED_SUMMARY brand=rpaloop "
            f"processes={counts['processes']} steps={counts['steps']} materials={counts['materials']} "
            f"runs={counts['runs']} runsteps={counts['runsteps']} "
            f"interventions={counts['interventions']} users={counts['users']}"
        )
        return counts
    finally:
        db.close()


if __name__ == "__main__":
    seed()
