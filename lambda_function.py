import json
import traceback

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from shared.env_loader import load_secrets
load_secrets()

from request_handler import parse_request
from routing import dispatch


def handler(event, context):
    method = event.get("httpMethod", "?")
    path   = event.get("path", "?")

    if method == "OPTIONS":
        return _response(200, {})

    try:
        req              = parse_request(event)
        status_code, data = dispatch(req["method"], req["path"], req["body"])
        print(f"[{status_code}] {req['method']} {req['path']}")
        return _response(status_code, data)
    except ValueError as e:
        print(f"[400] {method} {path}: {e}")
        return _response(400, {"message": str(e)})
    except Exception as e:
        print(f"[500] {method} {path}: {e}")
        traceback.print_exc()
        return _response(500, {"message": "Internal server error"})


def _response(status_code: int, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
        },
        "body": json.dumps(body, default=str),
    }
