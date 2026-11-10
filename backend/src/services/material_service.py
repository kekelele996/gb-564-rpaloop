from sqlalchemy import select

from src.models.material import Material
from src.services.serializers import material_out
from src.utils.credit_code import validate_credit_code
from src.utils.errors import AppError


def _sync_credit(material: Material) -> None:
    valid, reason = validate_credit_code(material.credit_code)
    material.credit_valid = valid
    material.credit_reason = reason


def list_materials(db, only_invalid: bool = False) -> list[dict]:
    query = select(Material).order_by(Material.id)
    if only_invalid:
        query = query.where(Material.credit_valid.is_(False))
    return [material_out(item) for item in db.scalars(query).all()]


def get_material(db, material_id: int) -> Material:
    material = db.get(Material, material_id)
    if material is None:
        raise AppError(404, "MATERIAL_NOT_FOUND", f"企业材料 {material_id} 不存在")
    return material


def create_material(db, payload: dict) -> dict:
    company = payload["company_name"].strip()
    exists = db.scalars(select(Material).where(Material.company_name == company)).first()
    if exists:
        raise AppError(409, "MATERIAL_EXISTS", f"企业 {company} 已存在材料档案")
    material = Material(
        company_name=company,
        credit_code=payload["credit_code"].strip().upper(),
        contact=payload.get("contact", ""),
        attachments=payload.get("attachments", []),
        validity_date=payload.get("validity_date"),
        missing_flags=payload.get("missing_flags", []),
    )
    _sync_credit(material)
    db.add(material)
    db.commit()
    db.refresh(material)
    return material_out(material)


def validate_material(db, material_id: int) -> dict:
    """只读校验：重新执行 GB 32100 校验位算法，不写库（审计只读角色也可调用）。"""
    material = get_material(db, material_id)
    valid, reason = validate_credit_code(material.credit_code)
    return {
        "material_id": material.id,
        "company_name": material.company_name,
        "credit_code": material.credit_code,
        "valid": valid,
        "reason": reason,
        "can_declare": bool(valid) and not material.missing_flags,
        "missing_flags": material.missing_flags or [],
    }
