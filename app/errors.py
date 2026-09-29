def explain(code: int) -> str:
    return {409: "conflict", 422: "bad field"}.get(code, "unknown")
