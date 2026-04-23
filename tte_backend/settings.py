from pathlib import Path
import os
from dotenv import load_dotenv
from datetime import timedelta


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "accounts",
    "storages",
    "corsheaders",
    "rest_framework",
    "mptt",
    "django_filters",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CORS_ALLOWED_ORIGINS = [h.strip() for h in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if h.strip()]

CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", False)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "accounts.permissions.BlockAccessUntilPasswordChanged",
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}

REST_FRAMEWORK["DEFAULT_FILTER_BACKENDS"] = [
    "django_filters.rest_framework.DjangoFilterBackend",
]

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

INSTALLED_APPS += ["rest_framework_simplejwt.token_blacklist"]


AUTHENTICATION_BACKENDS = [
    "accounts.auth_backends.NIPHashBackend",
    "accounts.backends.LegacyPinBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_USER_MODEL = "accounts.User"

ROOT_URLCONF = "tte_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "tte_backend.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "tte"),
        "USER": os.getenv("DB_USER", "root"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "init_command": os.getenv("DB_OPTIONS_INIT_COMMAND", "SET sql_mode='STRICT_TRANS_TABLES'"),
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = os.getenv("LANGUAGE_CODE", "id")
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Jakarta")
USE_I18N = os.getenv("USE_I18N", True)
USE_TZ = os.getenv("USE_TZ", True)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ADMIN_SITE_HEADER = os.getenv("ADMIN_SITE_HEADER", "TTE Admin")
ADMIN_SITE_TITLE = os.getenv("ADMIN_SITE_TITLE", "TTE Admin")
ADMIN_INDEX_TITLE = os.getenv("ADMIN_INDEX_TITLE", "Administrasi")

# minio
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")

MINIO_REGION = os.getenv("MINIO_REGION", "us-east-1")
MINIO_STATIC_BUCKET = os.getenv("MINIO_STATIC_BUCKET", "tte-static")
MINIO_MEDIA_BUCKET = os.getenv("MINIO_MEDIA_BUCKET", "tte-media")

# ===== django-storages / boto3 =====
AWS_ACCESS_KEY_ID = MINIO_ACCESS_KEY
AWS_SECRET_ACCESS_KEY = MINIO_SECRET_KEY
AWS_S3_ENDPOINT_URL = MINIO_ENDPOINT
AWS_S3_REGION_NAME = MINIO_REGION

AWS_S3_USE_SSL = os.getenv("AWS_S3_USE_SSL", False)
AWS_S3_VERIFY = os.getenv("AWS_S3_VERIFY", False)
AWS_S3_ADDRESSING_STYLE = os.getenv("AWS_S3_ADDRESSING_STYLE", "path")
AWS_DEFAULT_ACL = os.getenv("AWS_DEFAULT_ACL", None)

AWS_QUERYSTRING_AUTH = os.getenv("AWS_QUERYSTRING_AUTH", True)
AWS_QUERYSTRING_EXPIRE = int(os.getenv("AWS_QUERYSTRING_EXPIRE", "900"))

AWS_S3_SIGNATURE_VERSION = os.getenv("AWS_S3_SIGNATURE_VERSION", "s3v4")

STORAGES = {
    "default": {
        "BACKEND": "core.storages.PrivateMediaStorage",
        "OPTIONS": {},
    },
    "staticfiles": {
        "BACKEND": "core.storages.StaticStorage",
        "OPTIONS": {},
    },
}

STATIC_URL = os.getenv("STATIC_URL", f"{MINIO_ENDPOINT}/{MINIO_STATIC_BUCKET}/")
MEDIA_URL  = os.getenv("MEDIA_URL", f"{MINIO_ENDPOINT}/{MINIO_MEDIA_BUCKET}/") 

STATIC_ROOT = os.getenv("STATIC_ROOT", "staticfiles")

PDP_ENC_KEY = os.getenv("PDP_ENC_KEY", "dev-enc-key-change-me")
ESIGN = {
    "URL" : os.getenv("ESIGN_URL", "https://[IP_ADDRESS]/api/sign/pdf"),
    "USERNAME": os.getenv("ESIGN_USERNAME", ""),
    "PASSWORD": os.getenv("ESIGN_PASSWORD", "")
}

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://tte.bekasikab.go.id")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "[EMAIL_ADDRESS]")

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "[IP_ADDRESS]")
EMAIL_PORT = os.getenv("EMAIL_PORT", 587)
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", False)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")

DEFAULT_RESET_EMAIL_DOMAIN = os.getenv("DEFAULT_RESET_EMAIL_DOMAIN", "bekasikab.go.id")
