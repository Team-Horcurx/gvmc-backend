import boto3
import json
import os

_loaded = False


def load_secrets():
    global _loaded
    if _loaded:
        return
    secret_name = os.environ.get("SECRET_NAME", "").strip()
    if not secret_name:
        # local dev — .env values used directly
        _loaded = True
        return
    try:
        client = boto3.client("secretsmanager", region_name="ap-south-1")
        response = client.get_secret_value(SecretId=secret_name)
        secrets = json.loads(response["SecretString"])
        for k, v in secrets.items():
            if k not in os.environ:
                os.environ[k] = str(v)
        _loaded = True
        print(f"[EnvLoader] Loaded {len(secrets)} keys from {secret_name}")
    except Exception as e:
        print(f"[EnvLoader] Secrets Manager unavailable, using env vars: {e}")
        _loaded = True
