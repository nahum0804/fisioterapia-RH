import json

def pack_fields(description: str, user_comment: str | None, considerations: str | None) -> str:
    return json.dumps({
        "description": description or "",
        "comment": user_comment,
        "considerations": considerations,
        "_v": 1
    }, ensure_ascii=False)

def unpack_fields(raw_comment: str | None):
    if not raw_comment:
        return {"description": "", "comment": None, "considerations": None}

    try:
        data = json.loads(raw_comment)
        if isinstance(data, dict) and "description" in data:
            return {
                "description": data.get("description") or "",
                "comment": data.get("comment"),
                "considerations": data.get("considerations"),
            }
    except Exception:
        pass

    return {"description": "", "comment": raw_comment, "considerations": None}
