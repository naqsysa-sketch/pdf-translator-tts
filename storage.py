import io
import os
import logging
from typing import Optional

import boto3
import requests
from botocore.client import Config

logger = logging.getLogger("pdf_translator.storage")

S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
S3_PUBLIC_ENDPOINT_URL = os.getenv("S3_PUBLIC_ENDPOINT_URL")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "pdf-translator-assets")
S3_PRESIGNED_EXPIRY = int(os.getenv("S3_PRESIGNED_EXPIRY", "3600"))

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "media")
SUPABASE_SIGNED_URL_EXPIRY = int(os.getenv("SUPABASE_SIGNED_URL_EXPIRY", "604800"))

S3_REF_PREFIX = "s3ref:"
SB_REF_PREFIX = "sbref:"


def get_outputs_dir() -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return "/tmp/outputs"
    return os.path.join(base, "static", "outputs")


def local_media_url(file_path: str) -> str:
    name = os.path.basename(file_path)
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return f"/api/media/{name}"
    return f"/static/outputs/{name}"


def supabase_storage_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)


def is_sb_ref(value: Optional[str]) -> bool:
    return bool(value and value.startswith(SB_REF_PREFIX))


def make_sb_ref(bucket: str, object_path: str) -> str:
    return f"{SB_REF_PREFIX}{bucket}/{object_path}"


def parse_sb_ref(ref: str) -> tuple[str, str]:
    payload = ref[len(SB_REF_PREFIX):]
    bucket, _, object_path = payload.partition("/")
    return bucket, object_path


def _supabase_headers(content_type: Optional[str] = None) -> dict:
    headers = {"Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def ensure_supabase_bucket(bucket: str = SUPABASE_STORAGE_BUCKET) -> None:
    if not supabase_storage_configured():
        return
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/storage/v1/bucket/{bucket}",
            headers=_supabase_headers(),
            timeout=30,
        )
        if resp.status_code == 200:
            return
        create = requests.post(
            f"{SUPABASE_URL}/storage/v1/bucket",
            headers={**_supabase_headers("application/json")},
            json={"id": bucket, "name": bucket, "public": False},
            timeout=30,
        )
        if create.status_code not in (200, 201, 409):
            logger.warning(f"Could not ensure Supabase bucket '{bucket}': {create.text}")
    except Exception as exc:
        logger.warning(f"Supabase bucket check failed: {exc}")


def upload_bytes_to_supabase(data: bytes, object_path: str, content_type: str) -> str:
    ensure_supabase_bucket()
    bucket = SUPABASE_STORAGE_BUCKET
    resp = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/{bucket}/{object_path}",
        headers={**_supabase_headers(content_type), "x-upsert": "true"},
        data=data,
        timeout=120,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Supabase upload failed ({resp.status_code}): {resp.text[:200]}")
    logger.info(f"Uploaded to Supabase Storage: {bucket}/{object_path}")
    return make_sb_ref(bucket, object_path)


def upload_file_to_supabase(file_path: str, object_path: str, content_type: str) -> str:
    with open(file_path, "rb") as handle:
        return upload_bytes_to_supabase(handle.read(), object_path, content_type)


def get_supabase_signed_url(ref: str, expires_in: Optional[int] = None) -> str:
    bucket, object_path = parse_sb_ref(ref)
    expiry = expires_in or SUPABASE_SIGNED_URL_EXPIRY
    resp = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/sign/{bucket}/{object_path}",
        headers={**_supabase_headers("application/json")},
        json={"expiresIn": expiry},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Supabase sign URL failed ({resp.status_code}): {resp.text[:200]}")
    signed = resp.json().get("signedURL") or resp.json().get("signedUrl")
    if not signed:
        raise RuntimeError("Supabase sign URL response missing signedURL")
    if signed.startswith("http"):
        return signed
    if signed.startswith("/storage/v1"):
        return f"{SUPABASE_URL}{signed}"
    if signed.startswith("/object/"):
        return f"{SUPABASE_URL}/storage/v1{signed}"
    return f"{SUPABASE_URL}{signed}"


def download_supabase_ref(ref: str) -> Optional[bytes]:
    try:
        url = get_supabase_signed_url(ref)
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            return response.content
    except Exception as exc:
        logger.error(f"Failed to download Supabase object {ref}: {exc}")
    return None


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
    Upload to Supabase Storage, S3/MinIO, or local path (in that order).
    Returns an internal storage reference, not a public URL.
    """
    if supabase_storage_configured():
        try:
            return upload_file_to_supabase(file_path, object_name, content_type)
        except Exception as exc:
            logger.error(f"Supabase Storage upload failed for {object_name}: {exc}")

    client = get_s3_client()
    if not client:
        logger.info(f"No cloud storage configured. Keeping local file for {object_name}")
        return local_media_url(file_path)

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
        return local_media_url(file_path)


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
    """Turn stored ref into a browser-accessible URL."""
    if not stored_value:
        return None

    if is_sb_ref(stored_value) and supabase_storage_configured():
        try:
            return get_supabase_signed_url(stored_value)
        except Exception as exc:
            logger.error(f"Failed to sign Supabase URL for {stored_value}: {exc}")

    object_name = extract_object_name(stored_value)
    if object_name and get_s3_client():
        try:
            return generate_presigned_url(object_name)
        except Exception as exc:
            logger.error(f"Failed to presign {object_name}: {exc}")

    if stored_value.startswith("/static/outputs/"):
        if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
            return f"/api/media/{stored_value.split('/')[-1]}"
        return stored_value

    if stored_value.startswith("/api/media/"):
        return stored_value

    if stored_value.startswith("http"):
        return stored_value

    return stored_value


def read_stored_file(stored_value: Optional[str], local_outputs_dir: str) -> Optional[bytes]:
    """Read file bytes from cloud ref, legacy URL, or local path."""
    if not stored_value:
        return None

    if is_sb_ref(stored_value):
        data = download_supabase_ref(stored_value)
        if data:
            return data

    object_name = extract_object_name(stored_value)
    if object_name:
        client = get_s3_client()
        if client:
            try:
                buffer = io.BytesIO()
                client.download_fileobj(S3_BUCKET_NAME, object_name, buffer)
                buffer.seek(0)
                return buffer.read()
            except Exception as exc:
                logger.error(f"Failed to download S3 object {object_name}: {exc}")

    if stored_value.startswith("http"):
        try:
            download_url = stored_value
            if S3_ENDPOINT_URL and "localhost:9000" in download_url and "minio:9000" in S3_ENDPOINT_URL:
                download_url = download_url.replace("localhost:9000", "minio:9000")
            response = requests.get(download_url, timeout=30)
            if response.status_code == 200:
                return response.content
        except Exception as exc:
            logger.error(f"Failed to fetch legacy URL {stored_value}: {exc}")

    if stored_value.startswith("/static/outputs/") or stored_value.startswith("/api/media/"):
        filename = stored_value.split("/")[-1]
        local_path = os.path.join(local_outputs_dir, filename)
        if os.path.exists(local_path):
            with open(local_path, "rb") as handle:
                return handle.read()
        alt_path = os.path.join(get_outputs_dir(), filename)
        if os.path.exists(alt_path):
            with open(alt_path, "rb") as handle:
                return handle.read()

    return None


def download_stored_file_to_path(stored_value: str, dest_path: str) -> bool:
    """Download a stored ref to a local file path."""
    data = read_stored_file(stored_value, get_outputs_dir())
    if not data:
        return False
    os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
    with open(dest_path, "wb") as handle:
        handle.write(data)
    return True
