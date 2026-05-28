"""
MintNews Network V3 — Application Factory
app.py — Master entrypoint with all module registrations
"""

import os
import logging
from datetime import datetime, timezone

import sentry_sdk
from flask import Flask, render_template, jsonify, request, g
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_caching import Cache
from flask_socketio import SocketIO
from sentry_sdk.integrations.flask import FlaskIntegration
from loguru import logger

from config import get_config

# ──────────────────────────────────────────────────────────────
# EXTENSION INSTANCES (initialized without app)
# ──────────────────────────────────────────────────────────────
db       = SQLAlchemy()
migrate  = Migrate()
login_mgr = LoginManager()
mail     = Mail()
limiter  = Limiter(key_func=get_remote_address)
cache    = Cache()
socketio = SocketIO()
cors     = CORS()


# ──────────────────────────────────────────────────────────────
# APPLICATION FACTORY
# ──────────────────────────────────────────────────────────────
def create_app(config_object=None) -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # ── Load Config ───────────────────────────────────────────
    cfg = config_object or get_config()
    app.config.from_object(cfg)

    # ── Sentry (Production Error Tracking) ───────────────────
    if app.config.get("SENTRY_DSN"):
        sentry_sdk.init(
            dsn=app.config["SENTRY_DSN"],
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.2,
            profiles_sample_rate=0.1,
            environment=os.environ.get("FLASK_ENV", "development"),
        )

    # ── Initialize Extensions ─────────────────────────────────
    _init_extensions(app)

    # ── Register Blueprints ───────────────────────────────────
    _register_blueprints(app)

    # ── Register Error Handlers ───────────────────────────────
    _register_error_handlers(app)

    # ── Register Context Processors ───────────────────────────
    _register_context_processors(app)

    # ── Register CLI Commands ─────────────────────────────────
    _register_cli_commands(app)

    # ── Shell Context ─────────────────────────────────────────
    @app.shell_context_processor
    def make_shell_context():
        from models import (
            User, Article, Category, Comment, TradingJournal,
            PriceAlert, Subscription, Transaction, Badge,
            Notification, Message, Poll, Community, MintCoin
        )
        return {"db": db, "User": User, "Article": Article}

    logger.info(f"✅ MintNews V3 started | ENV={os.environ.get('FLASK_ENV','dev')}")
    return app


# ──────────────────────────────────────────────────────────────
# EXTENSION INITIALIZATION
# ──────────────────────────────────────────────────────────────
def _init_extensions(app: Flask):
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        async_mode="eventlet",
        message_queue=app.config.get("REDIS_URL", None),
        logger=False,
        engineio_logger=False,
    )

    # ── Flask-Login Config ────────────────────────────────────
    login_mgr.init_app(app)
    login_mgr.login_view       = "auth.login"
    login_mgr.login_message    = "Please sign in to access this page."
    login_mgr.login_message_category = "warning"
    login_mgr.session_protection = "strong"

    @login_mgr.user_loader
    def load_user(user_id: str):
        from models.user import User
        return User.query.get(int(user_id))

    @login_mgr.request_loader
    def load_user_from_request(request):
        from modules.auth.utils import decode_jwt_from_request
        return decode_jwt_from_request(request)


# ──────────────────────────────────────────────────────────────
# BLUEPRINT REGISTRATION
# ──────────────────────────────────────────────────────────────
def _register_blueprints(app: Flask):
    # Core / Public
    from modules.core.routes       import core_bp
    from modules.auth.routes       import auth_bp
    from modules.news.routes       import news_bp
    from modules.trading.routes    import trading_bp
    from modules.ai.routes         import ai_bp
    from modules.community.routes  import community_bp
    from modules.gamification.routes import gamification_bp
    from modules.monetization.routes import monetization_bp
    from modules.analytics.routes   import analytics_bp
    from modules.admin.routes        import admin_bp

    # API v1
    from api.v1.news     import api_news_bp
    from api.v1.trading  import api_trading_bp
    from api.v1.user     import api_user_bp
    from api.v1.ai       import api_ai_bp
    from api.v1.webhooks import api_webhooks_bp

    # Register with URL prefixes
    blueprint_map = [
        (core_bp,          "/"),
        (auth_bp,          "/auth"),
        (news_bp,          "/news"),
        (trading_bp,       "/trading"),
        (ai_bp,            "/ai"),
        (community_bp,     "/community"),
        (gamification_bp,  "/rewards"),
        (monetization_bp,  "/account"),
        (analytics_bp,     "/analytics"),
        (admin_bp,         "/admin"),
        # REST API
        (api_news_bp,      "/api/v1/news"),
        (api_trading_bp,   "/api/v1/trading"),
        (api_user_bp,      "/api/v1/user"),
        (api_ai_bp,        "/api/v1/ai"),
        (api_webhooks_bp,  "/api/v1/webhooks"),
    ]

    for bp, prefix in blueprint_map:
        app.register_blueprint(bp, url_prefix=prefix)


# ──────────────────────────────────────────────────────────────
# ERROR HANDLERS
# ──────────────────────────────────────────────────────────────
def _register_error_handlers(app: Flask):
    @app.errorhandler(400)
    def bad_request(e):
        if request.is_json:
            return jsonify(error="Bad Request", message=str(e)), 400
        return render_template("errors/400.html", error=e), 400

    @app.errorhandler(401)
    def unauthorized(e):
        if request.is_json:
            return jsonify(error="Unauthorized"), 401
        return render_template("errors/401.html"), 401

    @app.errorhandler(403)
    def forbidden(e):
        if request.is_json:
            return jsonify(error="Forbidden"), 403
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        if request.is_json:
            return jsonify(error="Not Found"), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(429)
    def rate_limited(e):
        if request.is_json:
            return jsonify(error="Rate limit exceeded. Please slow down.", retry_after=str(e.retry_after)), 429
        return render_template("errors/429.html"), 429

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        logger.exception(f"Internal Server Error: {e}")
        if request.is_json:
            return jsonify(error="Internal Server Error"), 500
        return render_template("errors/500.html"), 500


# ──────────────────────────────────────────────────────────────
# CONTEXT PROCESSORS
# ──────────────────────────────────────────────────────────────
def _register_context_processors(app: Flask):
    @app.context_processor
    def inject_globals():
        from models.category import Category
        from models.notification import Notification
        from flask_login import current_user

        categories = cache.get("nav_categories")
        if not categories:
            categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order).limit(10).all()
            cache.set("nav_categories", categories, timeout=600)

        unread_count = 0
        if current_user.is_authenticated:
            unread_count = Notification.query.filter_by(
                user_id=current_user.id, is_read=False
            ).count()

        return {
            "app_name":     app.config["APP_NAME"],
            "app_version":  app.config["APP_VERSION"],
            "categories":   categories,
            "now":          datetime.now(timezone.utc),
            "unread_notifications": unread_count,
            "ga_id":        app.config.get("GA_MEASUREMENT_ID", ""),
            "feature_flags": {
                "ai":          app.config.get("FEATURE_AI_SUMMARY", True),
                "trading":     app.config.get("FEATURE_TRADING_HUB", True),
                "gamification": app.config.get("FEATURE_GAMIFICATION", True),
                "voice":       app.config.get("FEATURE_VOICE_ARTICLES", True),
                "pwa":         app.config.get("FEATURE_PWA", True),
            },
        }

    @app.before_request
    def before_request_hooks():
        g.request_start = datetime.now(timezone.utc)

    @app.after_request
    def after_request_hooks(response):
        # Security headers
        response.headers["X-Content-Type-Options"]    = "nosniff"
        response.headers["X-Frame-Options"]           = "SAMEORIGIN"
        response.headers["X-XSS-Protection"]          = "1; mode=block"
        response.headers["Referrer-Policy"]           = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"]        = "geolocation=(), microphone=(), camera=()"

        # Performance logging
        if hasattr(g, "request_start"):
            elapsed = (datetime.now(timezone.utc) - g.request_start).total_seconds() * 1000
            response.headers["X-Response-Time"] = f"{elapsed:.2f}ms"
            if elapsed > 1000:
                logger.warning(f"Slow request: {request.path} took {elapsed:.0f}ms")

        return response


# ──────────────────────────────────────────────────────────────
# CLI COMMANDS
# ──────────────────────────────────────────────────────────────
def _register_cli_commands(app: Flask):
    import click

    @app.cli.command("create-db")
    def create_db():
        """Initialize all database tables."""
        with app.app_context():
            db.create_all()
            click.echo("✅ Database tables created.")

    @app.cli.command("seed-db")
    def seed_db():
        """Seed database with initial data."""
        from utils.seed import run_seed
        with app.app_context():
            run_seed(db)
            click.echo("✅ Database seeded.")

    @app.cli.command("create-admin")
    @click.argument("email")
    @click.argument("password")
    def create_admin(email: str, password: str):
        """Create an admin user."""
        from models.user import User, UserRole
        with app.app_context():
            if User.query.filter_by(email=email).first():
                click.echo("⚠️  User already exists.")
                return
            admin = User(
                email=email,
                username=email.split("@")[0],
                role=UserRole.ADMIN,
                is_verified=True,
                is_active=True,
            )
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            click.echo(f"✅ Admin '{email}' created.")

    @app.cli.command("run-worker")
    def run_worker():
        """Start Celery background worker."""
        import subprocess
        subprocess.run([
            "celery", "-A", "tasks.celery_app", "worker",
            "--loglevel=info", "--concurrency=4"
        ])

    @app.cli.command("health-check")
    def health_check():
        """Run full system health check."""
        from utils.health import run_health_check
        with app.app_context():
            results = run_health_check()
            for service, status in results.items():
                icon = "✅" if status["ok"] else "❌"
                click.echo(f"{icon} {service}: {status['message']}")


# ──────────────────────────────────────────────────────────────
# CELERY FACTORY
# ──────────────────────────────────────────────────────────────
def create_celery(app: Flask = None):
    from celery import Celery
    app = app or create_app()
    celery = Celery(app.name)
    celery.config_from_object(app.config, namespace="CELERY")

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


# ──────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────
app = create_app()

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=app.config.get("DEBUG", False),
        use_reloader=False,
    )
