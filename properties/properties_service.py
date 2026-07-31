import json
from shared.db import get_connection, serialize_row


class PropertiesService:

    def get_property(self, obj, property_id, **_):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT p.id, p.ward_id, w.name AS ward_name,
                           p.lat, p.lng, p.area_sqm, p.detection_type,
                           p.confidence, p.confidence_breakdown,
                           p.detected_at, p.s3_geojson_key,
                           p.status, p.notes, p.updated_by, p.updated_at AS verified_at,
                           p.ai_explanation
                    FROM properties p
                    JOIN wards w ON w.id = p.ward_id
                    WHERE p.id = %s
                """, (property_id,))
                row = cur.fetchone()

        if not row:
            return 404, {"message": "Property not found"}

        result = serialize_row(row)
        if isinstance(result.get("confidence_breakdown"), str):
            try:
                result["confidence_breakdown"] = json.loads(result["confidence_breakdown"])
            except Exception:
                pass
        return 200, result
