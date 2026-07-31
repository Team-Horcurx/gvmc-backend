import uuid
import os
from datetime import datetime

from shared.db import get_connection, serialize_rows, serialize_row
from shared.s3_client import get_presigned_put_url, get_bucket

VALID_REVIEW_STATUSES = {"under_review", "resolved"}


class TicketsService:

    def create_ticket(self, obj, **_):
        ward_id     = obj.get("ward_id", "").strip()
        house_number = obj.get("house_number", "").strip()
        description = obj.get("description", "").strip()
        property_id = obj.get("property_id") or None
        tax_pending = obj.get("tax_pending") or None
        photo_s3_key = obj.get("photo_s3_key") or None

        if not ward_id:
            return 400, {"message": "ward_id is required"}
        if not house_number:
            return 400, {"message": "house_number is required"}
        if not description:
            return 400, {"message": "description is required"}

        ticket_id = str(uuid.uuid4())

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM wards WHERE id = %s", (ward_id,))
                if not cur.fetchone():
                    return 404, {"message": "Ward not found"}

                if property_id:
                    cur.execute("SELECT id FROM properties WHERE id = %s", (property_id,))
                    if not cur.fetchone():
                        property_id = None

                cur.execute("""
                    INSERT INTO tickets
                        (id, ward_id, property_id, house_number, description,
                         tax_pending, photo_s3_key)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (ticket_id, ward_id, property_id, house_number, description,
                      tax_pending, photo_s3_key))

        return 201, {"id": ticket_id, "status": "open"}

    def list_tickets(self, obj, **_):
        ward_id = obj.get("ward_id") or None
        status  = obj.get("status")  or None

        conditions = []
        params = []
        if ward_id:
            conditions.append("t.ward_id = %s")
            params.append(ward_id)
        if status:
            conditions.append("t.status = %s")
            params.append(status)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT
                        t.id, t.ward_id, w.name AS ward_name,
                        t.property_id, t.house_number, t.description,
                        t.tax_pending, t.photo_s3_key,
                        t.status, t.supervisor_notes,
                        t.reviewed_by, t.reviewed_at,
                        t.created_at, t.updated_at
                    FROM tickets t
                    JOIN wards w ON w.id = t.ward_id
                    {where}
                    ORDER BY t.created_at DESC
                """, params)
                rows = cur.fetchall()

        return 200, {"tickets": serialize_rows(rows)}

    def get_ticket(self, obj, ticket_id, **_):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        t.id, t.ward_id, w.name AS ward_name,
                        t.property_id, t.house_number, t.description,
                        t.tax_pending, t.photo_s3_key,
                        t.status, t.supervisor_notes,
                        t.reviewed_by, t.reviewed_at,
                        t.created_at, t.updated_at
                    FROM tickets t
                    JOIN wards w ON w.id = t.ward_id
                    WHERE t.id = %s
                """, (ticket_id,))
                row = cur.fetchone()

        if not row:
            return 404, {"message": "Ticket not found"}

        ticket = serialize_row(row)
        if ticket.get("photo_s3_key"):
            from shared.s3_client import get_presigned_url
            ticket["photo_url"] = get_presigned_url(ticket["photo_s3_key"])

        return 200, {"ticket": ticket}

    def review_ticket(self, obj, ticket_id, **_):
        status          = obj.get("status", "")
        supervisor_notes = obj.get("supervisor_notes", "")
        reviewed_by     = obj.get("reviewed_by", "supervisor")

        if status not in VALID_REVIEW_STATUSES:
            return 400, {"message": f"status must be one of: {', '.join(sorted(VALID_REVIEW_STATUSES))}"}

        now = datetime.utcnow()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM tickets WHERE id = %s", (ticket_id,))
                if not cur.fetchone():
                    return 404, {"message": "Ticket not found"}

                cur.execute("""
                    UPDATE tickets
                    SET status = %s, supervisor_notes = %s,
                        reviewed_by = %s, reviewed_at = %s
                    WHERE id = %s
                """, (status, supervisor_notes, reviewed_by, now, ticket_id))

        return 200, {"status": status}

    def get_photo_upload_url(self, obj, **_):
        filename = obj.get("filename", "photo.jpg")
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
        allowed = {"jpg", "jpeg", "png", "heic", "webp"}
        if ext not in allowed:
            ext = "jpg"

        key = f"uploads/tickets/{uuid.uuid4()}.{ext}"
        content_type = "image/jpeg" if ext in {"jpg", "jpeg"} else f"image/{ext}"
        upload_url = get_presigned_put_url(key, content_type=content_type)

        return 200, {"upload_url": upload_url, "s3_key": key}
