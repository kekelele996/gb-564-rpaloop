def paginate(items: list, offset: int = 0, limit: int = 100) -> dict:
    total = len(items)
    return {"total": total, "offset": offset, "limit": limit, "items": items[offset: offset + limit]}
