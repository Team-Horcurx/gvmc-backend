import os
import base64
from datetime import datetime
import boto3

from shared.db import get_connection
from shared.s3_client import get_bucket, put_object

REGION = "ap-south-1"


class AdminService:

    def upload_csv(self, obj, **_):
        file_content = obj.get("file_content") or obj.get("body")
        filename     = obj.get("filename", "assessment_data.csv")

        if not file_content:
            return 400, {"message": "file_content is required"}

        try:
            content_bytes = base64.b64decode(file_content)
        except Exception:
            content_bytes = file_content.encode("utf-8") if isinstance(file_content, str) else b""

        key = f"uploads/{filename}"
        try:
            put_object(key, content_bytes, "text/csv")
        except Exception as e:
            print(f"[ADMIN] S3 upload failed: {e}")

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO admin_config (key_name, value, updated_at) VALUES ('data_mode', 'live', %s)
                    ON DUPLICATE KEY UPDATE value = 'live', updated_at = VALUES(updated_at)
                """, (datetime.utcnow(),))

        return 200, {"properties_imported": 0, "message": "CSV uploaded. System switched to Live mode."}

    def db_config(self, obj, **_):
        allowed = {"ndbi_threshold", "min_area_sqm", "cloud_cover_max"}
        updates = {k: str(v) for k, v in obj.items() if k in allowed}

        if not updates:
            return 200, {}

        with get_connection() as conn:
            with conn.cursor() as cur:
                for key, value in updates.items():
                    cur.execute("""
                        INSERT INTO admin_config (key_name, value, updated_at) VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE value = VALUES(value), updated_at = VALUES(updated_at)
                    """, (key, value, datetime.utcnow()))

        return 200, {}

    def refresh_pipeline(self, obj, **_):
        ec2_id = os.environ.get("EC2_INSTANCE_ID", "")

        if ec2_id:
            try:
                ssm = boto3.client("ssm", region_name=REGION)
                ssm.send_command(
                    InstanceIds=[ec2_id],
                    DocumentName="AWS-RunShellScript",
                    Parameters={"commands": [
                        "cd /opt/gvmc-pipeline && bash run_pipeline.sh >> /var/log/gvmc-pipeline.log 2>&1 &"
                    ]},
                )
            except Exception as e:
                print(f"[ADMIN] SSM trigger failed: {e}")

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO admin_config (key_name, value, updated_at) VALUES ('pipeline_status', 'running', %s)
                    ON DUPLICATE KEY UPDATE value = 'running', updated_at = VALUES(updated_at)
                """, (datetime.utcnow(),))

        return 200, {"triggered": True}
