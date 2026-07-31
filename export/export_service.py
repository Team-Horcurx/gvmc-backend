from datetime import datetime
from shared.db import get_connection, serialize_rows
from shared.s3_client import export_rows_to_csv


class ExportService:

    def export_csv(self, obj, **_):
        ward_id = obj.get("ward_id")
        where   = "WHERE p.ward_id = %s" if ward_id else ""
        params  = [ward_id] if ward_id else []

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT p.id, w.name AS ward_name, p.lat, p.lng,
                           p.area_sqm, p.detection_type, p.confidence,
                           p.detected_at,
                           COALESCE(vs.status, 'pending') AS verification_status,
                           vs.updated_by, vs.notes
                    FROM properties p
                    JOIN wards w ON w.id = p.ward_id
                    LEFT JOIN verification_status vs ON vs.property_id = p.id
                    {where}
                    ORDER BY p.confidence DESC
                """, params)
                rows = cur.fetchall()

        rows = serialize_rows(rows)
        key  = f"exports/gvmc_properties_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

        try:
            url = export_rows_to_csv(rows, key)
        except Exception as e:
            print(f"[EXPORT] S3 upload failed: {e}")
            return 503, {"message": "Export failed — S3 unavailable"}

        return 200, {"presigned_url": url, "row_count": len(rows)}
