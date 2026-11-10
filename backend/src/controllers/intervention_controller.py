from src.services import intervention_service


def list_interventions(db, status=None, reason=None) -> dict:
    items = intervention_service.list_interventions(db, status, reason)
    return {"total": len(items), "items": items}


def resolve(db, user, intervention_id: int, payload: dict) -> dict:
    return intervention_service.resolve(db, user, intervention_id, payload["action"],
                                        payload.get("resolution", ""))
