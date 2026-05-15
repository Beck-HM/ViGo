"""ViGo Standard Library: Cloud Storage (cloudlib)
Provides S3-compatible object storage, local file sync, and URL utilities.
Uses urllib for presigned operations, optional boto3 for full S3 support.
"""
import os
import urllib.request
import urllib.parse
import json
import hashlib
import base64
import hmac
from datetime import datetime, timedelta
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


def register(env):
    """Register all cloudlib functions into the given ViGo environment."""

    # ── S3 Client (boto3 optional, HTTP fallback) ──

    def _s3_sign_v4(access_key, secret_key, region, service, method, bucket, key,
                     headers=None, payload_hash="UNSIGNED-PAYLOAD", expires=3600):
        """Generate a presigned URL using AWS Signature V4."""
        amz_date = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        date_stamp = datetime.utcnow().strftime("%Y%m%d")
        credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
        host = f"{bucket}.s3.{region}.amazonaws.com"

        canonical_headers = f"host:{host}\n"
        signed_headers = "host"
        canonical_request = (
            f"{method}\n/{key}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        )
        string_to_sign = (
            f"AWS4-HMAC-SHA256\n{amz_date}\n{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode()).hexdigest()}"
        )

        def sign(key, msg):
            return hmac.new(key, msg.encode(), hashlib.sha256).digest()

        k_date = sign(("AWS4" + secret_key).encode(), date_stamp)
        k_region = sign(k_date, region)
        k_service = sign(k_region, service)
        k_signing = sign(k_service, "aws4_request")
        signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()

        return (f"https://{host}/{key}"
                f"?X-Amz-Algorithm=AWS4-HMAC-SHA256"
                f"&X-Amz-Credential={access_key}/{credential_scope}"
                f"&X-Amz-Date={amz_date}"
                f"&X-Amz-Expires={expires}"
                f"&X-Amz-SignedHeaders={signed_headers}"
                f"&X-Amz-Signature={signature}")

    def s3_upload(filepath, bucket, key, endpoint_url=None, access_key=None, secret_key=None, region="us-east-1"):
        """Upload a file to S3 or S3-compatible storage."""
        try:
            import boto3
            client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key or os.environ.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=secret_key or os.environ.get("AWS_SECRET_ACCESS_KEY"),
                region_name=region,
            )
            client.upload_file(filepath, bucket, key)
            return f"s3://{bucket}/{key}"
        except ImportError:
            raise ViGoError("boto3 not installed. Run: pip install boto3")

    def s3_download(bucket, key, filepath, endpoint_url=None, access_key=None, secret_key=None, region="us-east-1"):
        """Download a file from S3 or S3-compatible storage."""
        try:
            import boto3
            client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key or os.environ.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=secret_key or os.environ.get("AWS_SECRET_ACCESS_KEY"),
                region_name=region,
            )
            client.download_file(bucket, key, filepath)
            return filepath
        except ImportError:
            raise ViGoError("boto3 not installed. Run: pip install boto3")

    def s3_list(bucket, prefix="", endpoint_url=None, access_key=None, secret_key=None, region="us-east-1"):
        """List objects in an S3 bucket."""
        try:
            import boto3
            client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key or os.environ.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=secret_key or os.environ.get("AWS_SECRET_ACCESS_KEY"),
                region_name=region,
            )
            paginator = client.get_paginator('list_objects_v2')
            result = []
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for obj in page.get('Contents', []):
                    result.append({"key": obj['Key'], "size": obj['Size'],
                                   "modified": str(obj['LastModified'])})
            return result
        except ImportError:
            raise ViGoError("boto3 not installed. Run: pip install boto3")

    def s3_delete(bucket, key, endpoint_url=None, access_key=None, secret_key=None, region="us-east-1"):
        try:
            import boto3
            client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key or os.environ.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=secret_key or os.environ.get("AWS_SECRET_ACCESS_KEY"),
                region_name=region,
            )
            client.delete_object(Bucket=bucket, Key=key)
            return True
        except ImportError:
            raise ViGoError("boto3 not installed. Run: pip install boto3")

    def s3_presigned_url(bucket, key, method="GET", expires=3600, access_key=None, secret_key=None, region="us-east-1"):
        """Generate a presigned URL for an S3 object (no boto3 required)."""
        ak = access_key or os.environ.get("AWS_ACCESS_KEY_ID")
        sk = secret_key or os.environ.get("AWS_SECRET_ACCESS_KEY")
        if not ak or not sk:
            raise ViGoError("AWS credentials required")
        return _s3_sign_v4(ak, sk, region, "s3", method.upper(), bucket, key, expires=int(expires))

    # ── HTTP upload/download (cloud-agnostic) ──

    def cloud_upload(filepath, url, headers=None):
        try:
            req_headers = headers if headers else {}
            with open(filepath, 'rb') as f:
                data = f.read()
            req = urllib.request.Request(url, data=data, headers=req_headers, method='PUT')
            with urllib.request.urlopen(req, timeout=300) as resp:
                return resp.status == 200
        except Exception as e:
            raise ViGoError(f"Upload failed: {e}")

    def cloud_download(url, filepath, headers=None):
        try:
            req_headers = headers if headers else {}
            req = urllib.request.Request(url, headers=req_headers)
            with urllib.request.urlopen(req, timeout=300) as resp:
                with open(filepath, 'wb') as f:
                    f.write(resp.read())
            return filepath
        except Exception as e:
            raise ViGoError(f"Download failed: {e}")

    # ── Object URL builder ──

    def s3_build_url(bucket, key, region="us-east-1", endpoint_url=None):
        if endpoint_url:
            base = endpoint_url.rstrip('/')
            return f"{base}/{bucket}/{key}"
        return f"https://{bucket}.s3.{region}.amazonaws.com/{urllib.parse.quote(key)}"

    # ── Registration ──

    env.define("s3_upload", BuiltinFunction(s3_upload, "s3_upload"))
    env.define("s3_download", BuiltinFunction(s3_download, "s3_download"))
    env.define("s3_list", BuiltinFunction(s3_list, "s3_list"))
    env.define("s3_delete", BuiltinFunction(s3_delete, "s3_delete"))
    env.define("s3_presigned_url", BuiltinFunction(s3_presigned_url, "s3_presigned_url"))
    env.define("s3_build_url", BuiltinFunction(s3_build_url, "s3_build_url"))
    env.define("cloud_upload", BuiltinFunction(cloud_upload, "cloud_upload"))
    env.define("cloud_download", BuiltinFunction(cloud_download, "cloud_download"))