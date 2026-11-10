"""GB 32100-2015 统一社会信用代码校验。

字符集 31 位（去掉 I/O/S/V/Z），前 17 位加权求和后取模 31 得到校验位。
"""
import re

CHARSET = "0123456789ABCDEFGHJKLMNPQRTUWXY"
WEIGHTS = [1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28]
_CODE_RE = re.compile(r"^[0-9A-HJ-NPQRTUWXY]{17}[0-9A-HJ-NPQRTUWXY]$")


def compute_check_digit(base17: str) -> str:
    if len(base17) != 17:
        raise ValueError("base17 must be 17 characters")
    total = 0
    for ch, weight in zip(base17, WEIGHTS):
        idx = CHARSET.find(ch)
        if idx < 0:
            raise ValueError(f"illegal character in credit code: {ch}")
        total += idx * weight
    check = 31 - (total % 31)
    if check == 31:
        check = 0
    return CHARSET[check]


def validate_credit_code(code: str) -> tuple[bool, str]:
    """返回 (是否合法, 原因)。原因在合法时为 ok。"""
    if not code:
        return False, "统一社会信用代码为空"
    normalized = code.strip().upper()
    if len(normalized) != 18:
        return False, f"长度应为 18 位，实际 {len(normalized)} 位"
    illegal = [ch for ch in normalized if ch not in CHARSET]
    if illegal:
        return False, f"含非法字符 {'/'.join(sorted(set(illegal)))}（GB 32100 排除 I/O/S/V/Z）"
    if not _CODE_RE.match(normalized):
        return False, "格式不符合 GB 32100 编码规则"
    try:
        expected = compute_check_digit(normalized[:17])
    except ValueError as exc:
        return False, str(exc)
    actual = normalized[17]
    if expected != actual:
        return False, f"校验位不匹配（应为 {expected}，实际 {actual}）"
    return True, "ok"
