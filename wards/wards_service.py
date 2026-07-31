import json
from shared.db import get_connection, serialize_rows, serialize_row
from shared.s3_client import get_presigned_url


def _build_bbox(row: dict) -> dict:
    return {
        "north": float(row.pop("bbox_north", 0) or 0),
        "south": float(row.pop("bbox_south", 0) or 0),
        "east":  float(row.pop("bbox_east", 0) or 0),
        "west":  float(row.pop("bbox_west", 0) or 0),
    }


class WardsService:

    def list_wards(self, obj, **_):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT w.id, w.name,
                           w.bbox_north, w.bbox_south, w.bbox_east, w.bbox_west,
                           w.geojson_s3,
                           COUNT(p.id) AS detection_count
                    FROM wards w
                    LEFT JOIN properties p ON p.ward_id = w.id
                    GROUP BY w.id, w.name, w.bbox_north, w.bbox_south, w.bbox_east, w.bbox_west, w.geojson_s3
                    ORDER BY w.id
                """)
                rows = cur.fetchall()

        result = []
        for r in serialize_rows(rows):
            r["bbox"] = _build_bbox(r)
            result.append(r)
        return 200, result

    def get_changes(self, obj, ward_id, **_):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT geojson_s3 FROM wards WHERE id = %s", (ward_id,))
                row = cur.fetchone()

        if not row or not row.get("geojson_s3"):
            return 404, {"message": "No GeoJSON found for this ward"}
        try:
            url = get_presigned_url(row["geojson_s3"])
        except Exception as e:
            print(f"[S3] presign failed: {e}")
            return 503, {"message": "GeoJSON not available right now"}
        return 200, {"presigned_url": url}

    def get_unassessed(self, obj, ward_id, **_):
        type_filter   = obj.get("type")
        status_filter = obj.get("status")

        where  = "WHERE p.ward_id = %s"
        params = [ward_id]

        if type_filter:
            where += " AND p.detection_type = %s"
            params.append(type_filter)
        if status_filter:
            where += " AND p.status = %s"
            params.append(status_filter)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT p.id, p.ward_id, w.name AS ward_name,
                           p.lat, p.lng, p.area_sqm, p.detection_type,
                           p.confidence, p.confidence_breakdown,
                           p.detected_at, p.s3_geojson_key,
                           p.status
                    FROM properties p
                    JOIN wards w ON w.id = p.ward_id
                    {where}
                    ORDER BY p.confidence DESC
                """, params)
                rows = cur.fetchall()

        result = serialize_rows(rows)
        for r in result:
            if isinstance(r.get("confidence_breakdown"), str):
                try:
                    r["confidence_breakdown"] = json.loads(r["confidence_breakdown"])
                except Exception:
                    pass
            r["ai_explanation"] = None
        return 200, result

    def get_alerts(self, obj, ward_id, **_):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, severity, text, ward_id, created_at FROM alerts WHERE ward_id = %s ORDER BY created_at DESC",
                    (ward_id,)
                )
                rows = cur.fetchall()
        return 200, serialize_rows(rows)
