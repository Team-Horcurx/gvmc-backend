import os
import csv
import io
import boto3

REGION = "ap-south-1"
_s3 = None


def _get_s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3", region_name=REGION)
    return _s3


def get_bucket() -> str:
    return os.environ.get("GVMC_S3_BUCKET", "gvmc-sw14-data")


def get_presigned_url(key: str, expiry: int = 3600) -> str:
    return _get_s3().generate_presigned_url(
        "get_object",
        Params={"Bucket": get_bucket(), "Key": key},
        ExpiresIn=expiry,
    )


def put_object(key: str, body: bytes, content_type: str = "application/octet-stream"):
    _get_s3().put_object(
        Bucket=get_bucket(),
        Key=key,
        Body=body,
        ContentType=content_type,
    )


def export_rows_to_csv(rows: list, key: str) -> str:
    if not rows:
        raise ValueError("No rows to export")
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    put_object(key, buf.getvalue().encode("utf-8"), "text/csv")
    return get_presigned_url(key)
