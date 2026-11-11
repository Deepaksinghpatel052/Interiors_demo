"""Django settings for the Interior Studio demo.

Everything environment- or client-specific comes from `.env` (see `.env.example`)
or from the `core.StudioSettings` model — never hard-coded here.
"""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    DEMO_MODE=(bool, True),
    AI_MOCK=(bool, True),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# Demo / sales settings
DEMO_MODE = env("DEMO_MODE")
# Product landing page (DEVNIXPLUS enquiry form) at "/" with the demo studio at "/demo/". Off: the studio site is "/".
LANDING_PAGE = DEMO_MODE and env.bool("LANDING_PAGE", default=False)
DEVNIX_WHATSAPP = env("DEVNIX_WHATSAPP", default="")
DEVNIX_NAME = env("DEVNIX_NAME", default="DEVNIXPLUS")

# AI assistant
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")
ANTHROPIC_MODEL = env("ANTHROPIC_MODEL", default="claude-opus-5-5")
# Server-side refusal fallback for supported models (a safety decline is retried on a fallback model).
ANTHROPIC_FALLBACKS = env.bool("ANTHROPIC_FALLBACKS", default=True)
AI_MOCK = env("AI_MOCK") or not ANTHROPIC_API_KEY
# Assistant limits
AI_MAX_MESSAGE_CHARS = 500
AI_PUBLIC_LIMIT = (15, 600)      # messages per chat session per 10 minutes
AI_IP_LIMIT = (40, 3600)         # messages per IP per hour

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # project apps
    "core",
    "website",
    "crm",
    "bookings",
    "studio",
    "finance",
    "portal",
    "assistant",
    "automations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.modules.ModuleGateMiddleware",
]

ROOT_URLCONF = "config.urls"

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
                "core.context_processors.studio",
            ],
            "builtins": ["core.templatetags.studio"],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# India-first locale
LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True
DATE_FORMAT = "d-m-Y"
SHORT_DATE_FORMAT = "d-m-Y"
DATETIME_FORMAT = "d-m-Y, h:i A"
DATE_INPUT_FORMATS = ["%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"]

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Upload limits (validated again per field in forms)
MAX_UPLOAD_MB = 8
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

LOGIN_URL = "core:login"
LOGIN_REDIRECT_URL = "core:after_login"
LOGOUT_REDIRECT_URL = "/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Hashed static file names in production so browsers never use stale CSS/JS after an update.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG
                    else "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"},
}

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# Running behind the server's nginx (Docker deploy). Only enable these when the app port is reachable
# from nginx alone (docker-compose binds it to 127.0.0.1), otherwise clients could fake the headers.
if env.bool("BEHIND_HTTPS_PROXY", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
TRUST_X_REAL_IP = env.bool("TRUST_X_REAL_IP", default=False)   # nginx sets X-Real-IP = visitor's address

# One cache shared by all gunicorn workers and the scheduler container (rate limits, AI index version).
if env("CACHE_DIR", default=""):
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
                          "LOCATION": env("CACHE_DIR")}}

# Faster, isolated test runs: cheap password hashing and a throw-away media folder.
import sys  # noqa: E402

if len(sys.argv) > 1 and sys.argv[1] == "test":
    import tempfile

    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="studio-test-media-"))
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
