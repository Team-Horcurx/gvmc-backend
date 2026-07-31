from shared.db import get_connection, serialize_rows


class StatsService:

    def get_stats(self, obj, **_):
        ward_id = obj.get("ward_id")
        where   = "WHERE p.ward_id = %s" if ward_id else ""
        params  = [ward_id] if ward_id else []

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT
                        COUNT(*)                                                         AS total_detections,
                        SUM(detection_type = 'new_build')                                AS new_builds,
                        SUM(detection_type = 'change_of_use')                            AS change_of_use,
                        SUM(COALESCE(status, 'pending') = 'pending')                     AS pending_verification,
                        SUM(status = 'verified')                                         AS verified,
                        SUM(status = 'false_positive')                                   AS false_positives,
                        SUM(
                            CASE WHEN COALESCE(status,'pending') IN ('pending','underassessed')
                            THEN area_sqm * IF(detection_type='new_build', 80, 40)
                            ELSE 0 END
                        )                                                                AS revenue_estimate
                    FROM properties p
                    {where}
                """, params)
                row = cur.fetchone()

                cur.execute("""
                    SELECT key_name, value FROM admin_config
                    WHERE key_name IN ('data_mode','pipeline_status','last_refresh','ndbi_threshold')
                """)
                cfg = {r["key_name"]: r["value"] for r in cur.fetchall()}

        return 200, {
            "total_detections":     int(row["total_detections"]     or 0),
            "new_builds":           int(row["new_builds"]           or 0),
            "change_of_use":        int(row["change_of_use"]        or 0),
            "pending_verification": int(row["pending_verification"]  or 0),
            "verified":             int(row["verified"]              or 0),
            "false_positives":      int(row["false_positives"]       or 0),
            "revenue_estimate":     float(row["revenue_estimate"]    or 0),
            "ward_id":              ward_id,
            "data_mode":            cfg.get("data_mode", "demo"),
            "pipeline_status":      cfg.get("pipeline_status", "idle"),
            "last_refresh":         cfg.get("last_refresh"),
            "ndbi_threshold":       float(cfg.get("ndbi_threshold") or 0.15),
        }

    def get_all_wards(self, obj, **_):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        w.id AS ward_id, w.name AS ward_name,
                        COUNT(DISTINCT p.id)                     AS total_detections,
                        SUM(p.detection_type = 'new_build')      AS unassessed_count,
                        COALESCE(t.open_tickets, 0)              AS open_tickets,
                        COALESCE(t.resolved_tickets, 0)          AS resolved_tickets
                    FROM wards w
                    LEFT JOIN properties p ON p.ward_id = w.id
                    LEFT JOIN (
                        SELECT ward_id,
                               SUM(status IN ('open','under_review')) AS open_tickets,
                               SUM(status = 'resolved')               AS resolved_tickets
                        FROM tickets
                        GROUP BY ward_id
                    ) t ON t.ward_id = w.id
                    GROUP BY w.id, w.name
                    ORDER BY unassessed_count DESC
                """)
                ward_rows = cur.fetchall()

                cur.execute("""
                    SELECT
                        COUNT(*)                                                         AS total_detections,
                        SUM(detection_type = 'new_build')                                AS new_builds,
                        SUM(detection_type = 'change_of_use')                            AS change_of_use,
                        SUM(COALESCE(status,'pending') = 'pending')                      AS pending_verification,
                        SUM(status = 'verified')                                         AS verified,
                        SUM(status = 'false_positive')                                   AS false_positives,
                        SUM(
                            CASE WHEN COALESCE(status,'pending') IN ('pending','underassessed')
                            THEN area_sqm * IF(detection_type='new_build', 80, 40)
                            ELSE 0 END
                        )                                                                AS revenue_estimate
                    FROM properties
                """)
                totals_row = cur.fetchone()

                cur.execute("""
                    SELECT
                        COUNT(*)                                   AS total_tickets,
                        SUM(status IN ('open','under_review'))     AS open_tickets,
                        SUM(status = 'resolved')                   AS resolved_tickets
                    FROM tickets
                """)
                ticket_totals = cur.fetchone()

        wards = [
            {
                "ward_id":          str(r["ward_id"]),
                "ward_name":        r["ward_name"],
                "total_detections": int(r["total_detections"] or 0),
                "unassessed_count": int(r["unassessed_count"] or 0),
                "open_tickets":     int(r["open_tickets"]     or 0),
                "resolved_tickets": int(r["resolved_tickets"] or 0),
                "ai_brief":         None,
            }
            for r in ward_rows
        ]

        totals = {
            "total_detections":     int(totals_row["total_detections"]     or 0),
            "new_builds":           int(totals_row["new_builds"]           or 0),
            "change_of_use":        int(totals_row["change_of_use"]        or 0),
            "pending_verification": int(totals_row["pending_verification"]  or 0),
            "verified":             int(totals_row["verified"]              or 0),
            "false_positives":      int(totals_row["false_positives"]       or 0),
            "revenue_estimate":     float(totals_row["revenue_estimate"]    or 0),
            "total_tickets":        int(ticket_totals["total_tickets"]      or 0),
            "open_tickets":         int(ticket_totals["open_tickets"]       or 0),
            "resolved_tickets":     int(ticket_totals["resolved_tickets"]   or 0),
            "ward_id":              None,
        }

        return 200, {"wards": wards, "ai_brief": None, "totals": totals}
