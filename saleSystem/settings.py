"""
Django settings for saleSystem project.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


# =========================================
# BASE DIRECTORY / ENVIRONMENT
# =========================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    """
    環境変数の true / false をBooleanへ変換する。
    """
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def env_list(name, default=""):
    """
    カンマ区切りの環境変数をリストへ変換する。
    """
    value = os.getenv(name, default)

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


# =========================================
# SECURITY
# =========================================

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-local-development-only-change-this",
)

DEBUG = env_bool(
    "DEBUG",
    default=True,
)

ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS",
    default=(
        "127.0.0.1,"
        "localhost,"
        "sale-system-884085651960.asia-northeast1.run.app"
    ),
)

CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    default=(
        "http://127.0.0.1:8000,"
        "http://localhost:8000,"
        "https://sale-system-884085651960.asia-northeast1.run.app"
    ),
)

# Cloud Runなど、HTTPSプロキシ配下で正しくHTTPS判定するための設定
SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG


# =========================================
# APPLICATIONS
# =========================================

INSTALLED_APPS = [
    # Django標準
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # django-allauth
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",

    # saleSystem
    "publicity",
]


# =========================================
# DJANGO SITES
# =========================================

SITE_ID = 1


# =========================================
# AUTHENTICATION
# =========================================

AUTHENTICATION_BACKENDS = [
    # Django管理画面・スーパーユーザー用
    "django.contrib.auth.backends.ModelBackend",

    # Googleログイン用
    "allauth.account.auth_backends.AuthenticationBackend",
]

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_REDIRECT_URL = "/"

# Googleログイン後に、独自の教員メール照合を実行する
SOCIALACCOUNT_ADAPTER = (
    "publicity.adapters.TeacherSocialAccountAdapter"
)

# 登録済みメールであれば、追加の新規登録フォームを省略する
SOCIALACCOUNT_AUTO_SIGNUP = True

# Google認証情報のアクセストークンをDBへ保存しない
SOCIALACCOUNT_STORE_TOKENS = False

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
        "OAUTH_PKCE_ENABLED": True,
    }
}


# =========================================
# MIDDLEWARE
# =========================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # 静的ファイル配信
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",

    # django-allauth必須
    "allauth.account.middleware.AccountMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# =========================================
# URLS
# =========================================

ROOT_URLCONF = "saleSystem.urls"


# =========================================
# TEMPLATES
# =========================================

TEMPLATES = [
    {
        "BACKEND": (
            "django.template.backends.django."
            "DjangoTemplates"
        ),

        "DIRS": [],

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


# =========================================
# WSGI
# =========================================

WSGI_APPLICATION = "saleSystem.wsgi.application"


# =========================================
# DATABASE
# Supabase PostgreSQL
# =========================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",

        "NAME": os.getenv(
            "DB_NAME",
            "postgres",
        ),

        "USER": os.getenv(
            "DB_USER",
            "",
        ),

        "PASSWORD": os.getenv(
            "DB_PASSWORD",
            "",
        ),

        "HOST": os.getenv(
            "DB_HOST",
            "",
        ),

        "PORT": os.getenv(
            "DB_PORT",
            "6543",
        ),

        "OPTIONS": {
            "sslmode": "require",
        },

        # Supabase Transaction Poolerを利用するため、
        # 接続を長時間保持しない
        "CONN_MAX_AGE": 0,
    }
}


# =========================================
# PASSWORD VALIDATION
# =========================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# =========================================
# LANGUAGE / TIMEZONE
# =========================================

LANGUAGE_CODE = "ja"

TIME_ZONE = "Asia/Tokyo"

USE_I18N = True

USE_TZ = True


# =========================================
# STATIC FILES
# =========================================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]


# =========================================
# STORAGE / WHITENOISE
# =========================================

STORAGES = {
    "default": {
        "BACKEND": (
            "django.core.files.storage."
            "FileSystemStorage"
        ),
    },

    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage."
            "CompressedManifestStaticFilesStorage"
        ),
    },
}


# =========================================
# DEFAULT PRIMARY KEY
# =========================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"