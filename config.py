cat << 'EOF' > config.py
"""
MintNews Network V3 — Master Configuration
Supports: Development | Staging | Production
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────────────────────
# BASE CONFIG
# ──────────────────────────────────────────────────────────────
class Config:
    APP_NAME          = "MintNews Network V3"
    APP_VERSION       = "3.0.0"
    SECRET_KEY        = os.environ.get("SECRET_KEY", "mint-dev-secret-change-in-prod-!@#")
    WTF_CSRF_ENABLED  = True
    PROPAGATE_EXCEPTIONS = True

    # ── Database ──────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI      = os.environ.get(
        "DATABASE_URL", "sqlite:///mintnews_dev.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS      = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
    }

    # ── JWT ───────────────────────────────────────────────────
    JWT_SECRET_KEY            = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES  = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_COOKIE_SECURE         = False
    JWT_COOKIE_HTTPONLY       = True
    JWT_COOKIE_SAMESITE       = "Lax"

    # ── Sessions ──────────────────────────────────────────────
    SESSION_COOKIE_HTTPONLY  = True
    SESSION_COOKIE_SAMESITE  = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    REMEMBER_COOKIE_DURATION   = timedelta(days=30)

    # ── Rate Limiting ─────────────────────────────────────────
    RATELIMIT_DEFAULT         = "200 per day;50 per hour;10 per minute"
    RATELIMIT_STORAGE_URL     = os.environ.get("REDIS_URL", "memory://")
    RATELIMIT_HEADERS_ENABLED = True

    # ── Celery / Redis ────────────────────────────────────────
    CELERY_BROKER_URL         = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND     = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    CELERY_TASK_SERIALIZER    = "json"
    CELERY_RESULT_SERIALIZER  = "json"
    CELERY_ACCEPT_CONTENT     = ["json"]
    CELERY_TIMEZONE           = "UTC"
    CELERY_ENABLE_UTC         = True
    CELERY_BEAT_SCHEDULE      = {
        "fetch-news-every-15-min": {
            "task": "tasks.news_fetcher.fetch_all_sources",
            "schedule": 900,  # 15 minutes
        },
        "update-forex-prices": {
            "task": "tasks.trading_updater.refresh_prices",
            "schedule": 60,   # 1 minute
        },
        "cleanup-temp-accounts": {
            "task": "tasks.maintenance.cleanup_unverified_accounts",
            "schedule": 3600, # 1 hour
        },
        "daily-newsletter": {
            "task": "tasks.newsletter.send_daily_digest",
            "schedule": 86400, # 24 hours
        },
        "backup-database": {
            "task": "tasks.maintenance.backup_database",
            "schedule": 86400,
        },
    }

    # ── Cache ─────────────────────────────────────────────────
    CACHE_TYPE            = "redis"
    CACHE_REDIS_URL       = os.environ.get("REDIS_URL", "redis://localhost:6379/1")
    CACHE_DEFAULT_TIMEOUT = 300

    # ── Mail (Brevo / SMTP) ───────────────────────────────────
    MAIL_SERVER   = "smtp-relay.brevo.com"
    MAIL_PORT     = 587
    MAIL_USE_TLS  = True
    MAIL_USERNAME = os.environ.get("BREVO_SMTP_USER", "")
    MAIL_PASSWORD = os.environ.get("BREVO_SMTP_PASS", "")
    MAIL_DEFAULT_SENDER = ("MintNews Network", "noreply@mintnews.io")

    # ── API Keys ──────────────────────────────────────────────
    # News
    GNEWS_API_KEY     = os.environ.get("GNEWS_API_KEY", "")
    MARKETAUX_API_KEY = os.environ.get("MARKETAUX_API_KEY", "")
    NEWSAPI_KEY       = os.environ.get("NEWSAPI_KEY", "")

    # AI
    GROQ_API_KEY       = os.environ.get("GROQ_API_KEY", "")
    ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
    STABILITY_API_KEY  = os.environ.get("STABILITY_API_KEY", "")

    # Media
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY    = os.environ.get("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")

    # Finance
    ALPHA_VANTAGE_KEY = os.environ.get("ALPHA_VANTAGE_KEY", "")
    RAPIDAPI_KEY      = os.environ.get("RAPIDAPI_KEY", "")
    CRICAPI_KEY       = os.environ.get("CRICAPI_KEY", "")

    # Notifications
    ONESIGNAL_APP_ID  = os.environ.get("ONESIGNAL_APP_ID", "")
    ONESIGNAL_API_KEY = os.environ.get("ONESIGNAL_API_KEY", "")
    BREVO_API_KEY     = os.environ.get("BREVO_API_KEY", "")

    # Analytics
    GA_MEASUREMENT_ID = os.environ.get("GA_MEASUREMENT_ID", "")

    # Twitter / X
    TWITTER_CLIENT_ID     = os.environ.get("TWITTER_CLIENT_ID", "")
    TWITTER_CLIENT_SECRET = os.environ.get("TWITTER_CLIENT_SECRET", "")

    # Payments
    STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_SECRET_KEY      = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET  = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    RAZORPAY_KEY_ID        = os.environ.get("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET    = os.environ.get("RAZORPAY_KEY_SECRET", "")

    # OAuth
    GOOGLE_CLIENT_ID        = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET    = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    GITHUB_CLIENT_ID        = os.environ.get("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET    = os.environ.get("GITHUB_CLIENT_SECRET", "")

    # Sentry
    SENTRY_DSN = os.environ.get("SENTRY_DSN", "")

    # ── Feature Flags ─────────────────────────────────────────
    FEATURE_AI_SUMMARY     = True
    FEATURE_TRADING_HUB    = True
    FEATURE_GAMIFICATION   = True
    FEATURE_CRYPTO_PAYMENT = False  # Toggle for prod
    FEATURE_VOICE_ARTICLES = True
    FEATURE_PWA            = True

    # ── Upload Settings ───────────────────────────────────────
    MAX_CONTENT_LENGTH   = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER        = "static/uploads"
    ALLOWED_EXTENSIONS   = {"png", "jpg", "jpeg", "gif", "webp", "pdf", "mp3"}

    # ── Pagination ────────────────────────────────────────────
    NEWS_PER_PAGE    = 20
    COMMENTS_PER_PAGE = 25

    # ── Platform Tokens ───────────────────────────────────────
    MINTCOIN_DAILY_LOGIN    = 10
    MINTCOIN_ARTICLE_READ   = 2
    MINTCOIN_COMMENT_POST   = 5
    MINTCOIN_SHARE_ARTICLE  = 3
    MINTCOIN_REFERRAL       = 100

    # ── Trading Defaults ──────────────────────────────────────
    DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT", "EUR/USD", "GBP/USD", "XAU/USD"]
    PAPER_TRADE_BALANCE = 10000.0


class DevelopmentConfig(Config):
    DEBUG              = True
    TESTING            = False
    SQLALCHEMY_ECHO    = False
    JWT_COOKIE_SECURE  = False
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED   = True


class StagingConfig(Config):
    DEBUG   = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("STAGING_DATABASE_URL", Config.SQLALCHEMY_DATABASE_URI)
    JWT_COOKIE_SECURE       = True
    SESSION_COOKIE_SECURE   = True
    CACHE_TYPE              = "redis"


class ProductionConfig(Config):
    DEBUG   = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI   = os.environ.get("DATABASE_URL", "")
    JWT_COOKIE_SECURE         = True
    SESSION_COOKIE_SECURE     = True
    SESSION_COOKIE_SAMESITE   = "Strict"
    WTF_CSRF_ENABLED          = True
    SQLALCHEMY_ECHO           = False
    CACHE_TYPE                = "redis"
    # Force HTTPS
    PREFERRED_URL_SCHEME      = "https"


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "staging":     StagingConfig,
    "production":  ProductionConfig,
}


def get_config() -> Config:
    env = os.environ.get("FLASK_ENV", "development")
    return CONFIG_MAP.get(env, DevelopmentConfig)
EOF

