import csv
import io

from src.services.run_service import run_detail


def report_markdown(db, run_id: int) -> tuple[str, str]:
    data = run_detail(db, run_id)
    lines = [
        f"# 执行报告 {data['run_code']}",
        "",
        f"- 流程：{data['process_name']}（v{data['process_version']}）",
        f"- 企业：{data['company_name']} / {data['credit_code']}",
        f"- 机器人：{data['robot_name']}",
        f"- 触发方式：{data['trigger']}",
        f"- 状态：{data['status']}",
        f"- 步骤：{data['success_steps']}/{data['total_steps']}，重试 {data['retry_count']} 次",
        f"- 开始：{data['started_at']} 结束：{data['ended_at']}",
        f"- 拓扑序列：{data['execution_sequence']}",
        f"- 断点续跑跳过：{data['skipped_steps']}",
        "",
        "| # | 动作 | 目标 | 状态 | 尝试 | 定位器 | 耗时ms | 错误 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in data["run_steps"]:
        lines.append(
            f"| {item['seq']} | {item['action']} | {item['target_desc']} | {item['status']} | "
            f"{item['attempt']} | `{item['locator_strategy']}:{item['locator_used']}` | "
            f"{item['duration_ms']} | {item['error_code'] or ''} |"
        )
    if data["interventions"]:
        lines.extend(["", "## 接管记录", ""])
        for item in data["interventions"]:
            lines.append(
                f"- {item['code']} {item['reason']} → {item['status']}"
                f"（{item['action'] or '待处理'}）{item['resolution']} by {item['resolved_by'] or '-'}"
            )
    lines.extend(["", "## 执行日志", "", "```", data["log_text"] or "(空)", "```"])
    return "\n".join(lines), f"report-{data['run_code']}.md"


def report_csv(db, run_id: int) -> tuple[str, str]:
    data = run_detail(db, run_id)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["run_code", "process", "version", "company", "credit_code", "robot", "trigger",
                     "run_status", "success_steps", "total_steps", "retry_count", "started_at", "ended_at"])
    writer.writerow([data["run_code"], data["process_name"], data["process_version"], data["company_name"],
                     data["credit_code"], data["robot_name"], data["trigger"], data["status"],
                     data["success_steps"], data["total_steps"], data["retry_count"],
                     data["started_at"], data["ended_at"]])
    writer.writerow([])
    writer.writerow(["seq", "action", "target_desc", "status", "attempt", "locator_used",
                     "duration_ms", "error_code", "error_message", "idempotency_key", "note"])
    for item in data["run_steps"]:
        writer.writerow([item["seq"], item["action"], item["target_desc"], item["status"], item["attempt"],
                         item["locator_used"], item["duration_ms"], item["error_code"] or "",
                         item["error_message"], item["idempotency_key"], item["note"]])
    return buffer.getvalue(), f"report-{data['run_code']}.csv"
