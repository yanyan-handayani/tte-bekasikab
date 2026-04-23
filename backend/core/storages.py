from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings


class StaticStorage(S3Boto3Storage):
    bucket_name = settings.MINIO_STATIC_BUCKET if hasattr(settings, "MINIO_STATIC_BUCKET") else "tte-static"
    default_acl = None
    querystring_auth = False  # static public
    custom_domain = None
    location = ""


class PrivateMediaStorage(S3Boto3Storage):
    """
    Media private (surat, lampiran, dsb).
    Menggunakan presigned URL (AWS_QUERYSTRING_AUTH=True).
    """
    bucket_name = settings.MINIO_MEDIA_BUCKET if hasattr(settings, "MINIO_MEDIA_BUCKET") else "tte-media"
    default_acl = None
    querystring_auth = True
    custom_domain = None
    location = ""  # root bucket (path ditentukan oleh upload_to)
