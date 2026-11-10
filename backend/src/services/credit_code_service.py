from src.utils.credit_code import validate_credit_code


def inspect_credit_code(code: str, contact: str = "", company_name: str = "") -> dict:
    valid, reason = validate_credit_code(code)
    return {
        "credit_code": (code or "").strip().upper(),
        "valid": valid,
        "reason": reason,
        "company_name": company_name,
        "contact": contact,
    }
