import json


def parse_request(event: dict) -> dict:
    method = event.get("httpMethod", "GET").upper()
    path   = event.get("path", "/")

    raw_body = event.get("body") or "{}"
    try:
        body = json.loads(raw_body) if isinstance(raw_body, str) else (raw_body or {})
    except (json.JSONDecodeError, TypeError):
        body = {}

    query = event.get("queryStringParameters") or {}
    for k, v in query.items():
        if k not in body:
            body[k] = v

    return {"method": method, "path": path, "body": body}
