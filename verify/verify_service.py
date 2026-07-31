from datetime import datetime
from shared.db import get_connection

VALID_STATUSES = {"pending", "verified", "underassessed", "false_positive", "already_assessed"}


class VerifyService:

    def update_status(self, obj, property_id, **_):
        status     = obj.get("status", "")
        updated_by = obj.get("updated_by", "officer")
        notes      = obj.get("notes", "")

        if status not in VALID_STATUSES:
            return 400, {"message": f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}"}

        now = datetime.utcnow()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM properties WHERE id = %s", (property_id,))
                if not cur.fetchone():
                    return 404, {"message": "Property not found"}

                cur.execute("""
                    UPDATE properties
                    SET status = %s, updated_by = %s, updated_at = %s, notes = %s
                    WHERE id = %s
                """, (status, updated_by, now, notes, property_id))

                cur.execute("""
                    INSERT INTO verification_status (property_id, status, updated_by, updated_at, notes)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        status = VALUES(status), updated_by = VALUES(updated_by),
                        updated_at = VALUES(updated_at), notes = VALUES(notes)
                """, (property_id, status, updated_by, now, notes))

        return 200, {"status": status}
