"""算法 A：定位器稳健性评分。

输入：步骤的 locator_candidates（策略 + 选择器），以及该步骤近 N 次 RunStep 命中记录
      （locator_used / attempt / status）。
输出：每个候选的 hit_rate、avg_attempt_score、specificity、dynamic_risk、score(0-100)，
      推荐主/备定位器，步骤风险等级与原因。
公式：score = 100 * (0.45*hit_rate + 0.20*avg_attempt_score + 0.20*(1-dynamic_risk) + 0.15*specificity)
失败态：无历史命中记录 → score=50，reason=no_history。
可复现：命中记录来自 seed 的 RunStep，重算入口相同（POST /api/processes/{id}/rescore）。
"""
import re

DYNAMIC_PATTERNS = [
    ("long_digits", re.compile(r"\d{4,}")),
    ("uuid", re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")),
    ("timestamp", re.compile(r"(?<!\d)\d{10,13}(?!\d)")),
    ("hash", re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{16,}(?![0-9a-fA-F])")),
]

STRATEGY_BASE = {"id": 0.85, "text": 0.80, "role": 0.75, "css": 0.55, "xpath": 0.35}
HISTORY_LIMIT = 8


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def dynamic_risk(candidate: dict) -> tuple[float, list[str]]:
    haystack = " ".join(
        str(candidate.get(key, "")) for key in ("selector", "desc", "attribute", "text")
    )
    flags = [name for name, pattern in DYNAMIC_PATTERNS if pattern.search(haystack)]
    if not flags:
        return 0.0, []
    return 1.0, flags


def specificity(candidate: dict) -> float:
    strategy = str(candidate.get("strategy", "css"))
    selector = str(candidate.get("selector", ""))
    base = STRATEGY_BASE.get(strategy, 0.50)
    depth = selector.count(">") if strategy == "css" else selector.count("//")
    depth_penalty = min(depth * 0.025, 0.20)
    length_penalty = min(max(len(selector) - 60, 0) * 0.004, 0.12)
    return round(_clamp(base - depth_penalty - length_penalty, 0.05, 1.0), 4)


def score_candidate(candidate: dict, history: list[dict]) -> dict:
    selector = str(candidate.get("selector", ""))
    total = len(history)
    used = [row for row in history if row.get("locator_used") == selector]
    hits = [row for row in used if row.get("status") in ("ok", "retried")]
    risk, flags = dynamic_risk(candidate)
    spec = specificity(candidate)

    if total == 0:
        hit_rate = 0.0
        avg_attempts = 1.0
        score = 50.0
        reason = "no_history"
    else:
        hit_rate = round(len(hits) / total, 4)
        avg_attempts = round(sum(int(row.get("attempt", 1)) for row in used) / len(used), 4) if used else 1.0
        attempt_score = round(1.0 / max(avg_attempts, 1.0), 4)
        raw = (
            0.45 * hit_rate
            + 0.20 * attempt_score
            + 0.20 * (1.0 - risk)
            + 0.15 * spec
        )
        score = round(raw * 100)
        reason = "scored"

    return {
        **candidate,
        "hits": len(hits),
        "samples": total,
        "hit_rate": hit_rate,
        "avg_attempts": avg_attempts,
        "avg_attempt_score": round(1.0 / max(avg_attempts, 1.0), 4),
        "specificity": spec,
        "dynamic_risk": risk,
        "dynamic_flags": flags,
        "score": score,
        "reason": reason,
    }


def score_step(step: dict, history: list[dict]) -> dict:
    candidates = [score_candidate(c, history) for c in (step.get("locator_candidates") or [])]
    if not candidates:
        return {
            "step_id": step.get("id"),
            "seq": step.get("seq"),
            "target_desc": step.get("target_desc", ""),
            "candidates": [],
            "robustness_score": 0.0,
            "risk_level": "high",
            "risk_reason": "缺少定位器候选，无法执行",
            "recommended_primary": "",
            "recommended_backup": "",
            "samples": len(history),
        }

    ranked = sorted(candidates, key=lambda item: item["score"], reverse=True)
    primary = candidates[0]
    recommended_primary = ranked[0]
    recommended_backup = ranked[1] if len(ranked) > 1 else ranked[0]
    best = ranked[0]["score"]

    risks = [c["reason"] for c in candidates]
    has_history = any(item != "no_history" for item in risks)
    if not has_history:
        risk_level = "medium"
        reasons = ["no_history：该步骤尚无运行命中记录，分数按 50 处理，建议先干跑积累样本"]
    else:
        risk_level = "low"
        reasons = []
        if recommended_primary["dynamic_flags"]:
            risk_level = "high"
            reasons.append(
                f"主定位器含动态片段 {'/'.join(recommended_primary['dynamic_flags'])}，页面改版即失效"
            )
        if primary["dynamic_risk"] >= 1.0 and risk_level != "high":
            risk_level = "high"
            reasons.append("当前主定位器含动态片段")
        if best < 55 and risk_level == "low":
            risk_level = "high"
            reasons.append(f"历史稳健分仅 {best}，低于高危阈值 55")
        elif best < 70 and risk_level == "low":
            risk_level = "medium"
            reasons.append(f"历史稳健分 {best}，建议补充文本定位器")
        if recommended_primary["selector"] != primary["selector"]:
            reasons.append("推荐把文本定位器设为主定位器")

    return {
        "step_id": step.get("id"),
        "seq": step.get("seq"),
        "target_desc": step.get("target_desc", ""),
        "candidates": candidates,
        "robustness_score": primary["score"],
        "best_score": best,
        "risk_level": risk_level,
        "risk_reason": "；".join(reasons) if reasons else "历史命中稳定，保持现有定位器",
        "recommended_primary": recommended_primary["selector"],
        "recommended_backup": recommended_backup["selector"],
        "samples": len(history),
    }
