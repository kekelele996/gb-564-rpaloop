from src.services import material_service


def list_materials(db, only_invalid: bool = False) -> dict:
    items = material_service.list_materials(db, only_invalid)
    invalid = sum(1 for item in items if not item["credit_valid"])
    return {"total": len(items), "invalid": invalid, "items": items}


def create_material(db, payload: dict) -> dict:
    return material_service.create_material(db, payload)


def validate_material(db, material_id: int) -> dict:
    return material_service.validate_material(db, material_id)
