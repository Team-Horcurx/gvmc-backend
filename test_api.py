"""
GVMC Backend API Test Suite
Run from gvmc-backend/ with venv active:
    python test_api.py
"""
import json
import sys
from dotenv import load_dotenv

load_dotenv()

from lambda_function import handler

# ── helpers ───────────────────────────────────────────────────────────────────

PASS = 0
FAIL = 0


def _call(method: str, path: str, body: dict = None, query: dict = None):
    event = {
        "httpMethod": method,
        "path": path,
        "body": json.dumps(body or {}),
        "queryStringParameters": query or None,
        "headers": {},
    }
    result = handler(event, None)
    status = result["statusCode"]
    data   = json.loads(result["body"])
    return status, data


def ok(label: str, status: int, data):
    global PASS
    PASS += 1
    preview = json.dumps(data, default=str)[:90]
    print(f"  ✓  {label}")
    print(f"       {status} → {preview}")


def fail(label: str, status: int, data, reason: str):
    global FAIL
    FAIL += 1
    print(f"  ✗  {label}  [{reason}]")
    print(f"       {status} → {json.dumps(data, default=str)[:90]}")


def section(title: str):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


def check(label: str, condition: bool, status: int, data, reason: str = "assertion failed"):
    if condition:
        ok(label, status, data)
    else:
        fail(label, status, data, reason)


# ── tests ─────────────────────────────────────────────────────────────────────

section("GET /api/wards")

status, data = _call("GET", "/api/wards")
check("returns 200", status == 200, status, data)
check("returns a list", isinstance(data, list), status, data, "expected list")
check("has 5 wards", len(data) >= 5, status, data, f"got {len(data)}")
if data:
    w = data[0]
    check("ward has id",   "id"   in w, status, w, "missing id")
    check("ward has name", "name" in w, status, w, "missing name")
    check("ward has bbox", "bbox" in w and isinstance(w["bbox"], dict), status, w, "missing bbox dict")
    check("bbox has north/south/east/west",
          all(k in w.get("bbox", {}) for k in ("north","south","east","west")),
          status, w, "incomplete bbox")
    check("ward has detection_count", "detection_count" in w, status, w, "missing detection_count")
    check("ward has geojson_s3",      "geojson_s3"      in w, status, w, "missing geojson_s3")

WARD_ID  = str(data[0]["id"]) if data else "1"
PROP_IDS = []   # filled after unassessed call


# ── ward changes ──────────────────────────────────────────────────────────────

section("GET /api/wards/:id/changes")

status, data = _call("GET", f"/api/wards/{WARD_ID}/changes")
# S3 may not be configured locally — accept 200 or 503
check("returns 200 or 503", status in (200, 503), status, data, f"unexpected {status}")
if status == 200:
    check("has presigned_url", "presigned_url" in data, status, data, "missing presigned_url")

status, data = _call("GET", "/api/wards/999/changes")
check("unknown ward → 404", status == 404, status, data, f"expected 404, got {status}")


# ── unassessed properties ─────────────────────────────────────────────────────

section("GET /api/wards/:id/unassessed")

status, data = _call("GET", f"/api/wards/{WARD_ID}/unassessed")
check("returns 200",      status == 200,         status, data)
check("returns a list",   isinstance(data, list), status, data, "expected list")
check("has properties",   len(data) > 0,          status, data, "got empty list")

if data:
    p = data[0]
    PROP_IDS = [x["id"] for x in data]
    check("property has id",              "id"              in p, status, p, "missing id")
    check("property has ward_id",         "ward_id"         in p, status, p, "missing ward_id")
    check("property has lat/lng",         "lat" in p and "lng" in p, status, p, "missing lat/lng")
    check("property has area_sqm",        "area_sqm"        in p, status, p, "missing area_sqm")
    check("property has detection_type",  "detection_type"  in p, status, p, "missing detection_type")
    check("property has confidence",      "confidence"      in p, status, p, "missing confidence")
    check("property has confidence_breakdown",
          "confidence_breakdown" in p and isinstance(p["confidence_breakdown"], dict),
          status, p, "missing/invalid confidence_breakdown")
    check("property has status",          "status"          in p, status, p, "missing status")
    check("property has detected_at",     "detected_at"     in p, status, p, "missing detected_at")

# type filter
status, data = _call("GET", f"/api/wards/{WARD_ID}/unassessed", query={"type": "new_build"})
check("type=new_build filter → 200",  status == 200, status, data)
if isinstance(data, list) and data:
    all_new = all(p.get("detection_type") == "new_build" for p in data)
    check("all results are new_build", all_new, status, data, "mixed types returned")

status, data = _call("GET", f"/api/wards/{WARD_ID}/unassessed", query={"type": "change_of_use"})
check("type=change_of_use filter → 200", status == 200, status, data)
if isinstance(data, list) and data:
    all_cou = all(p.get("detection_type") == "change_of_use" for p in data)
    check("all results are change_of_use", all_cou, status, data, "mixed types returned")

# status filter
status, data = _call("GET", f"/api/wards/{WARD_ID}/unassessed", query={"status": "pending"})
check("status=pending filter → 200", status == 200, status, data)
if isinstance(data, list) and data:
    check("all pending", all(p.get("status") == "pending" for p in data),
          status, data, "non-pending returned")


# ── alerts ────────────────────────────────────────────────────────────────────

section("GET /api/wards/:id/alerts")

status, data = _call("GET", f"/api/wards/{WARD_ID}/alerts")
check("returns 200",      status == 200,         status, data)
check("returns a list",   isinstance(data, list), status, data, "expected list")
check("has alerts",       len(data) > 0,          status, data, "no alerts found")
if data:
    a = data[0]
    check("alert has id",         "id"         in a, status, a, "missing id")
    check("alert has severity",   "severity"   in a, status, a, "missing severity")
    check("alert has text",       "text"        in a, status, a, "missing text")
    check("alert has ward_id",    "ward_id"    in a, status, a, "missing ward_id")
    check("alert has created_at", "created_at" in a, status, a, "missing created_at")
    check("severity is valid",
          a.get("severity") in ("danger","warning","info"),
          status, a, f"unknown severity: {a.get('severity')}")


# ── property detail ───────────────────────────────────────────────────────────

section("GET /api/properties/:id")

PROP_ID = PROP_IDS[0] if PROP_IDS else "prop-w1-001"

status, data = _call("GET", f"/api/properties/{PROP_ID}")
check("returns 200",  status == 200, status, data)
check("has id",       data.get("id") == PROP_ID, status, data, f"id mismatch: {data.get('id')}")
check("has ward_name","ward_name" in data, status, data, "missing ward_name")
check("has confidence_breakdown",
      isinstance(data.get("confidence_breakdown"), dict) and len(data["confidence_breakdown"]) > 0,
      status, data, "missing/empty confidence_breakdown")
check("has ai_explanation key", "ai_explanation" in data, status, data, "missing ai_explanation key")

status, data = _call("GET", "/api/properties/nonexistent-id-xyz")
check("unknown property → 404", status == 404, status, data, f"expected 404, got {status}")


# ── stats ─────────────────────────────────────────────────────────────────────

section("GET /api/stats")

status, data = _call("GET", "/api/stats")
check("returns 200",               status == 200, status, data)
check("has total_detections",      "total_detections"     in data, status, data)
check("has new_builds",            "new_builds"           in data, status, data)
check("has change_of_use",         "change_of_use"        in data, status, data)
check("has pending_verification",  "pending_verification" in data, status, data)
check("has verified",              "verified"             in data, status, data)
check("has false_positives",       "false_positives"      in data, status, data)
check("has revenue_estimate",      "revenue_estimate"     in data, status, data)
check("has data_mode",             "data_mode"            in data, status, data)
check("has pipeline_status",       "pipeline_status"      in data, status, data)
check("has ndbi_threshold",        "ndbi_threshold"       in data, status, data)
check("total = new + change_of_use",
      data.get("total_detections") == data.get("new_builds",0) + data.get("change_of_use",0),
      status, data, "totals don't add up")

# ward-scoped stats
status, data = _call("GET", "/api/stats", query={"ward_id": WARD_ID})
check("ward-scoped stats 200",     status == 200,   status, data)
check("ward_id in response",       data.get("ward_id") == WARD_ID, status, data,
      f"ward_id mismatch: {data.get('ward_id')}")


# ── all-wards stats ───────────────────────────────────────────────────────────

section("GET /api/stats/all-wards")

status, data = _call("GET", "/api/stats/all-wards")
check("returns 200",     status == 200, status, data)
check("has wards list",  isinstance(data.get("wards"), list) and len(data["wards"]) > 0,
      status, data, "missing or empty wards list")
check("has totals",      isinstance(data.get("totals"), dict), status, data, "missing totals")
check("has ai_brief key","ai_brief" in data, status, data, "missing ai_brief key")

if data.get("wards"):
    w = data["wards"][0]
    check("ward_entry has ward_id",          "ward_id"          in w, status, w)
    check("ward_entry has ward_name",        "ward_name"        in w, status, w)
    check("ward_entry has unassessed_count", "unassessed_count" in w, status, w)
    check("ward_entry has total_detections", "total_detections" in w, status, w)

totals = data.get("totals", {})
check("totals has total_detections",    "total_detections"     in totals, status, totals)
check("totals has revenue_estimate",    "revenue_estimate"     in totals, status, totals)


# ── verify property ───────────────────────────────────────────────────────────

section("POST /api/properties/:id/verify")

status, data = _call("POST", f"/api/properties/{PROP_ID}/verify",
                     {"status": "verified", "updated_by": "test-officer", "notes": "field confirmed"})
check("verify → 200",       status == 200, status, data)
check("returns status field", data.get("status") == "verified", status, data,
      f"status={data.get('status')}")

# confirm it persisted
status, data = _call("GET", f"/api/properties/{PROP_ID}")
check("status persisted in DB", data.get("status") == "verified", status, data,
      f"status still shows: {data.get('status')}")

# cycle through all valid statuses
for s in ("underassessed", "false_positive", "already_assessed", "pending"):
    status, data = _call("POST", f"/api/properties/{PROP_ID}/verify", {"status": s})
    check(f"set status={s} → 200", status == 200, status, data)

# invalid status
status, data = _call("POST", f"/api/properties/{PROP_ID}/verify", {"status": "bogus"})
check("invalid status → 400", status == 400, status, data, f"expected 400, got {status}")

# unknown property
status, data = _call("POST", "/api/properties/nonexistent/verify", {"status": "verified"})
check("unknown property → 404", status == 404, status, data, f"expected 404, got {status}")


# ── export ────────────────────────────────────────────────────────────────────

section("POST /api/alerts/export")

status, data = _call("POST", "/api/alerts/export")
# S3 may not be configured locally — accept 200 or 503
check("export → 200 or 503", status in (200, 503), status, data, f"unexpected {status}")
if status == 200:
    check("has presigned_url", "presigned_url" in data, status, data)
    check("has row_count",     "row_count"     in data, status, data)

# ward-scoped export
status, data = _call("POST", "/api/alerts/export", {"ward_id": WARD_ID})
check("ward-scoped export → 200 or 503", status in (200, 503), status, data)


# ── admin endpoints ───────────────────────────────────────────────────────────

section("POST /api/admin/db-config")

status, data = _call("POST", "/api/admin/db-config", {"ndbi_threshold": 0.20, "min_area_sqm": 60})
check("db-config → 200", status == 200, status, data)

# verify ndbi_threshold saved
from shared.db import get_connection
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT value FROM admin_config WHERE key_name = 'ndbi_threshold'")
        row = cur.fetchone()
check("ndbi_threshold saved to DB",
      row and float(row["value"]) == 0.20, 200,
      row, f"stored: {row}")

# restore original
_call("POST", "/api/admin/db-config", {"ndbi_threshold": 0.15})

section("POST /api/admin/upload-csv")

import base64
csv_content = base64.b64encode(b"ward_id,area,type\n1,200,new_build\n").decode()
status, data = _call("POST", "/api/admin/upload-csv",
                     {"file_content": csv_content, "filename": "test_upload.csv"})
# S3 upload may fail locally — accept 200
check("upload-csv → 200", status == 200, status, data, f"got {status}")
if status == 200:
    check("has message", "message" in data, status, data)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM admin_config WHERE key_name = 'data_mode'")
            row = cur.fetchone()
    check("data_mode switched to live", row and row["value"] == "live", 200, row)
    # reset back to demo
    _call("POST", "/api/admin/db-config", {})
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE admin_config SET value='demo' WHERE key_name='data_mode'")

section("POST /api/admin/refresh")

status, data = _call("POST", "/api/admin/refresh")
check("refresh → 200",      status == 200,       status, data)
check("triggered=True",     data.get("triggered") is True, status, data,
      f"triggered={data.get('triggered')}")

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT value FROM admin_config WHERE key_name = 'pipeline_status'")
        row = cur.fetchone()
check("pipeline_status set to running", row and row["value"] == "running", 200, row)

# reset
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("UPDATE admin_config SET value='idle' WHERE key_name='pipeline_status'")


# ── chat ──────────────────────────────────────────────────────────────────────

section("POST /api/chat")

status, data = _call("POST", "/api/chat", {"message": "show me pending properties in ward 4"})
check("chat → 200",         status == 200, status, data)
check("has response field", "response" in data, status, data, "missing response key")
check("response is string", isinstance(data.get("response"), str), status, data)
check("response not empty", len(data.get("response", "")) > 0, status, data)

status, data = _call("POST", "/api/chat", {})
check("empty message → 400", status == 400, status, data, f"expected 400, got {status}")


# ── CORS / OPTIONS ────────────────────────────────────────────────────────────

section("OPTIONS (CORS preflight)")

status, data = _call("OPTIONS", "/api/wards")
check("OPTIONS → 200", status == 200, status, data)


# ── 404 fallback ─────────────────────────────────────────────────────────────

section("404 fallback")

status, data = _call("GET", "/api/does-not-exist")
check("unknown route → 404", status == 404, status, data, f"expected 404, got {status}")


# ── summary ───────────────────────────────────────────────────────────────────

print(f"\n{'═'*60}")
total = PASS + FAIL
print(f"  Results: {PASS}/{total} passed", "✓" if FAIL == 0 else f"  ({FAIL} failed)")
print(f"{'═'*60}\n")

if FAIL > 0:
    sys.exit(1)
