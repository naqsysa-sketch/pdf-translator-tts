import io
import os
import logging
from typing import Optional

import boto3
from botocore.client import Config

logger = logging.getLogger("pdf_translator.storage")

S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
S3_PUBLIC_ENDPOINT_URL = os.getenv("S3_PUBLIC_ENDPOINT_URL")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "pdf-translator-assets")
S3_PRESIGNED_EXPIRY = int(os.getenv("S3_PRESIGNED_EXPIRY", "3600"))

S3_REF_PREFIX = "s3ref:"


def get_s3_client(endpoint_url: Optional[str] = None):
    if not S3_ACCESS_KEY or not S3_SECRET_KEY:
        return None
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url or S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        config=Config(signature_version="s3v4"),
    )


def get_presign_client():
    """Client used to generate browser-facing presigned URLs (public domain/HTTPS)."""
    public_endpoint = S3_PUBLIC_ENDPOINT_URL or S3_ENDPOINT_URL
    return get_s3_client(endpoint_url=public_endpoint)


def is_s3_ref(value: Optional[str]) -> bool:
    return bool(value and value.startswith(S3_REF_PREFIX))


def make_s3_ref(object_name: str) -> str:
    return f"{S3_REF_PREFIX}{object_name}"


def get_object_name_from_ref(ref: str) -> str:
    return ref[len(S3_REF_PREFIX):]


def ensure_bucket_exists():
    client = get_s3_client()
    if not client:
        return
    try:
        client.head_bucket(Bucket=S3_BUCKET_NAME)
    except Exception:
        try:
            client.create_bucket(Bucket=S3_BUCKET_NAME)
            logger.info(f"Created private S3 bucket '{S3_BUCKET_NAME}' (no public read policy).")
        except Exception as e:
            logger.error(f"Failed to create S3 bucket: {e}")


def upload_file_to_s3(file_path: str, object_name: str, content_type: str) -> str:
    """
    Uploads a file to S3/MinIO and returns an internal s3ref: key (not a public URL).
    Falls back to local /static/outputs/ path when S3 is not configured.
    """
    client = get_s3_client()
    if not client:
        logger.info(f"S3 not configured. Keeping local file for {object_name}")
        return f"/static/outputs/{os.path.basename(file_path)}"

    try:
        ensure_bucket_exists()
        client.upload_file(
            file_path,
            S3_BUCKET_NAME,
            object_name,
            ExtraArgs={"ContentType": content_type},
        )
        logger.info(f"Uploaded {file_path} to S3 as {object_name}")
        return make_s3_ref(object_name)
    except Exception as e:
        logger.error(f"S3 upload failed for {object_name}: {e}")
        return f"/static/outputs/{os.path.basename(file_path)}"


def extract_object_name(stored_value: Optional[str]) -> Optional[str]:
    if not stored_value:
        return None
    if is_s3_ref(stored_value):
        return get_object_name_from_ref(stored_value)
    if S3_BUCKET_NAME and S3_BUCKET_NAME in stored_value:
        marker = f"{S3_BUCKET_NAME}/"
        if marker in stored_value:
            return stored_value.split(marker, 1)[1]
    return None


def generate_presigned_url(object_name: str, expires_in: Optional[int] = None) -> str:
    client = get_presign_client() or get_s3_client()
    if not client:
        raise ValueError("S3 client is not configured.")
    expiry = expires_in or S3_PRESIGNED_EXPIRY
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET_NAME, "Key": object_name},
        ExpiresIn=expiry,
    )


def resolve_media_url(stored_value: Optional[str]) -> Optional[str]:
    """Turn stored s3ref:/static/legacy URL into a browser-accessible URL."""
    if not stored_value:
        return None

    object_name = extract_object_name(stored_value)
    if object_name and get_s3_client():
        try:
            return generate_presigned_url(object_name)
        except Exception as e:
            logger.error(f"Failed to presign {object_name}: {e}")

    if stored_value.startswith("/static/"):
        return stored_value

    if stored_value.startswith("http"):
        return stored_value

    return stored_value


def read_stored_file(stored_value: Optional[str], local_outputs_dir: str) -> Optional[bytes]:
    """Read file bytes from S3 ref, legacy URL, or local static path."""
    if not stored_value:
        return None

    object_name = extract_object_name(stored_value)
    if object_name:
        client = get_s3_client()
        if client:
            try:
                buffer = io.BytesIO()
                client.download_fileobj(S3_BUCKET_NAME, object_name, buffer)
                buffer.seek(0)
                return buffer.read()
            except Exception as e:
                logger.error(f"Failed to download S3 object {object_name}: {e}")

    if stored_value.startswith("http"):
        try:
            import requests

            download_url = stored_value
            if S3_ENDPOINT_URL and "localhost:9000" in download_url and "minio:9000" in S3_ENDPOINT_URL:
                download_url = download_url.replace("localhost:9000", "minio:9000")
            response = requests.get(download_url, timeout=30)
            if response.status_code == 200:
                return response.content
        except Exception as e:
            logger.error(f"Failed to fetch legacy URL {stored_value}: {e}")

    if stored_value.startswith("/static/outputs/"):
        filename = stored_value.split("/")[-1]
        local_path = os.path.join(local_outputs_dir, filename)
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read()

    return None
