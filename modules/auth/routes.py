"""
MintNews Network V3 — Authentication Module
modules/auth/routes.py
Features: OAuth2, JWT, RBAC, 2FA, Magic Link, Rate Limiting,
          Account Locking, GDPR, Session Management, Device Fingerprinting
"""

import hashlib
import json
import secrets
from datetime import datetime, timezone, timedelta
from functools import wraps
from typing import Optional

import jwt
import requests
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, jsonify, current_app, make_response, g, session
)
from flask_login import login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from user_agents import parse as parse_ua

from app import db, limiter, mail, cache
from models import User, UserSession, AuditLog, MintCoinTransaction
from modules.auth.forms import LoginForm, RegisterForm, TOTPForm, MagicLinkForm
from utils.email import send_email
from utils.geo import get_location_from_ip
from utils.security import generate_jwt, decode_jwt, hash_fingerprint

auth_bp = Blueprint("auth", __name__, template_folder="templates")


# ──────────────────────────────────────────────────────────────
# DECORATORS
# ──────────────────────────────────────────────────────────────
def role_required(*roles):
    """RBAC decorator: require one of the given roles."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login", next=request.url))
            if current_user.role.value not in roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("core.index"))
            return f(*args, **kwargs)
        return decorated
    return decorator


def premium_required(f):
    """Paywall decorator for premium content."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_premium:
            return render_template("monetization/paywall.html"), 403
        return f(*args, **kwargs)
    return decorated


def api_key_or_jwt(f):
    """API auth: accept JWT token or API key in header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return jsonify(error="Unauthorized"), 401
        user = decode_jwt_from_request(request)
        if not user:
            return jsonify(error="Invalid or expired token"), 401
        g.current_user = user
        return f(*args, **kwargs)
    return decorated


# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────
def _build_device_fingerprint(req) -> str:
    components = [
        req.headers.get("User-Agent", ""),
        req.headers.get("Accept-Language", ""),
        req.headers.get("Accept-Encoding", ""),
        req.remote_addr or "",
    ]
    return hash_fingerprint("||".join(components))


def _create_session(user: User, req) -> UserSession:
    ua_string = req.headers.get("User-Agent", "")
    ua = parse_ua(ua_string)
    ip = req.remote_addr
    geo = get_location_from_ip(ip)
    fingerprint = _build_device_fingerprint(req)

    sess = UserSession(
        user_id      = user.id,
        ip_address   = ip,
        user_agent   = ua_string[:500],
        device_type  = "mobile" if ua.is_mobile else "tablet" if ua.is_tablet else "desktop",
        browser      = f"{ua.browser.family} {ua.browser.version_string}",
        os           = f"{ua.os.family} {ua.os.version_string}",
        country      = geo.get("country"),
        city         = geo.get("city"),
        fingerprint  = fingerprint,
        expires_at   = datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.session.add(sess)
    return sess


def _send_login_alert(user: User, ip: str, country: str, device: str):
    """Send IP/location-based login alert email."""
    send_email(
        to=user.email,
        subject="New Login to MintNews",
        template="auth/emails/login_alert.html",
        context={
            "user": user, "ip": ip, "country": country,
            "device": device, "time": datetime.now(timezone.utc)
        }
    )


def decode_jwt_from_request(req) -> Optional[User]:
    token = req.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        token = req.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=["HS256"]
        )
        return User.query.get(payload.get("sub"))
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ──────────────────────────────────────────────────────────────
# ROUTES — REGISTRATION
# ──────────────────────────────────────────────────────────────
@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("core.dashboard"))

    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash("Email already registered.", "danger")
            return render_template("auth/register.html", form=form)

        if User.query.filter_by(username=form.username.data).first():
            flash("Username already taken.", "danger")
            return render_template("auth/register.html", form=form)

        user = User(
            username    = form.username.data.strip(),
            email       = form.email.data.lower().strip(),
            display_name= form.username.data,
        )
        user.set_password(form.password.data)
        user.avatar_initials = user.generate_avatar_initials()
        user.verification_token = secrets.token_urlsafe(32)

        # Check referral
        ref_code = request.args.get("ref") or form.referral_code.data if hasattr(form, 'referral_code') else None
        if ref_code:
            referrer = User.query.filter_by(referral_code=ref_code).first()
            if referrer:
                user.referred_by_id = referrer.id
                # Award referrer coins
                referrer.mintcoins += current_app.config["MINTCOIN_REFERRAL"]
                db.session.add(MintCoinTransaction(
                    user_id=referrer.id,
                    amount=current_app.config["MINTCOIN_REFERRAL"],
                    balance_after=referrer.mintcoins,
                    reason="referral_signup",
                    ref_type="user", ref_id=user.id
                ))

        db.session.add(user)
        db.session.commit()

        # Send verification email
        send_email(
            to=user.email,
            subject="Verify your MintNews account",
            template="auth/emails/verify_email.html",
            context={"user": user, "token": user.verification_token}
        )
        flash("Account created! Please check your email to verify.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/verify-email/<token>")
def verify_email(token: str):
    user = User.query.filter_by(verification_token=token).first_or_404()
    if user.is_verified:
        flash("Email already verified.", "info")
    else:
        user.is_verified = True
        user.verification_token = None
        # Award initial coins
        user.mintcoins += 50
        db.session.add(MintCoinTransaction(
            user_id=user.id, amount=50, balance_after=50,
            reason="email_verified"
        ))
        db.session.commit()
        flash("Email verified! Welcome to MintNews.", "success")
    return redirect(url_for("auth.login"))


# ──────────────────────────────────────────────────────────────
# ROUTES — LOGIN
# ──────────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("20 per hour;5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("core.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(
            (User.email == form.identifier.data.lower()) |
            (User.username == form.identifier.data)
        ).first()

        if not user or not user.check_password(form.password.data):
            if user:
                user.record_failed_login()
                db.session.commit()
            flash("Invalid credentials.", "danger")
            return render_template("auth/login.html", form=form)

        if user.is_locked:
            flash(f"Account temporarily locked. Try again after {user.locked_until.strftime('%H:%M UTC')}.", "danger")
            return render_template("auth/login.html", form=form)

        if not user.is_active:
            flash("Account disabled. Contact support.", "danger")
            return render_template("auth/login.html", form=form)

        # 2FA check
        if user.is_2fa_enabled:
            session["pending_2fa_user_id"] = user.id
            return redirect(url_for("auth.verify_2fa"))

        return _complete_login(user, form.remember_me.data)

    return render_template("auth/login.html", form=form)


@auth_bp.route("/verify-2fa", methods=["GET", "POST"])
def verify_2fa():
    user_id = session.get("pending_2fa_user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    user = User.query.get_or_404(user_id)
    form = TOTPForm()

    if form.validate_on_submit():
        if user.verify_totp(form.token.data):
            session.pop("pending_2fa_user_id", None)
            return _complete_login(user, remember=False)
        else:
            flash("Invalid 2FA code.", "danger")

    return render_template("auth/verify_2fa.html", form=form)


def _complete_login(user: User, remember: bool = False):
    user.reset_failed_logins()
    user.last_login_at = datetime.now(timezone.utc)
    user.last_login_ip = request.remote_addr
    user.check_and_update_streak()

    # Session record
    sess = _create_session(user, request)
    db.session.commit()

    # Alert if new location (compare country)
    if user.last_login_country and user.last_login_country != sess.country:
        _send_login_alert(user, sess.ip_address, sess.country, sess.device_type)
    user.last_login_country = sess.country

    # Issue JWT
    access_token  = generate_jwt(user.id, "access",  current_app.config["JWT_ACCESS_TOKEN_EXPIRES"])
    refresh_token = generate_jwt(user.id, "refresh", current_app.config["JWT_REFRESH_TOKEN_EXPIRES"])

    db.session.commit()
    login_user(user, remember=remember)

    # Daily login coins
    user.mintcoins += current_app.config["MINTCOIN_DAILY_LOGIN"]
    db.session.add(MintCoinTransaction(
        user_id=user.id, amount=current_app.config["MINTCOIN_DAILY_LOGIN"],
        balance_after=user.mintcoins, reason="daily_login"
    ))
    db.session.commit()

    resp = make_response(redirect(request.args.get("next") or url_for("core.dashboard")))
    resp.set_cookie(
        "access_token", access_token,
        httponly=current_app.config["JWT_COOKIE_HTTPONLY"],
        secure=current_app.config["JWT_COOKIE_SECURE"],
        samesite=current_app.config["JWT_COOKIE_SAMESITE"],
        max_age=3600
    )
    resp.set_cookie(
        "refresh_token", refresh_token,
        httponly=True,
        secure=current_app.config["JWT_COOKIE_SECURE"],
        samesite=current_app.config["JWT_COOKIE_SAMESITE"],
        max_age=30 * 86400
    )
    return resp


# ──────────────────────────────────────────────────────────────
# ROUTES — MAGIC LINK
# ──────────────────────────────────────────────────────────────
@auth_bp.route("/magic-link", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def magic_link_request():
    form = MagicLinkForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            token = user.generate_magic_link()
            db.session.commit()
            magic_url = url_for("auth.magic_link_verify", token=token, _external=True)
            send_email(
                to=user.email,
                subject="Your MintNews Magic Link",
                template="auth/emails/magic_link.html",
                context={"user": user, "magic_url": magic_url}
            )
        flash("If an account exists, a magic link has been sent.", "success")
    return render_template("auth/magic_link.html", form=form)


@auth_bp.route("/magic-link/verify/<token>")
def magic_link_verify(token: str):
    user = User.query.filter_by(magic_link_token=token).first()
    if not user or not user.verify_magic_link(token):
        flash("Magic link is invalid or expired.", "danger")
        return redirect(url_for("auth.magic_link_request"))
    db.session.commit()
    return _complete_login(user, remember=False)


# ──────────────────────────────────────────────────────────────
# ROUTES — OAUTH2
# ──────────────────────────────────────────────────────────────
@auth_bp.route("/oauth/google")
def oauth_google():
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    params = {
        "client_id":     current_app.config["GOOGLE_CLIENT_ID"],
        "redirect_uri":  url_for("auth.oauth_google_callback", _external=True),
        "response_type": "code",
        "scope":         "openid email profile",
        "state":         state,
    }
    from urllib.parse import urlencode
    return redirect("https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params))


@auth_bp.route("/oauth/google/callback")
def oauth_google_callback():
    if request.args.get("state") != session.pop("oauth_state", None):
        flash("OAuth state mismatch.", "danger")
        return redirect(url_for("auth.login"))

    code = request.args.get("code")
    token_resp = requests.post("https://oauth2.googleapis.com/token", data={
        "code":          code,
        "client_id":     current_app.config["GOOGLE_CLIENT_ID"],
        "client_secret": current_app.config["GOOGLE_CLIENT_SECRET"],
        "redirect_uri":  url_for("auth.oauth_google_callback", _external=True),
        "grant_type":    "authorization_code",
    }).json()

    userinfo = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {token_resp.get('access_token')}"}
    ).json()

    return _handle_oauth_user(
        provider="google",
        provider_id=userinfo.get("id"),
        email=userinfo.get("email"),
        name=userinfo.get("name"),
        avatar=userinfo.get("picture"),
    )


@auth_bp.route("/oauth/github")
def oauth_github():
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    from urllib.parse import urlencode
    params = {
        "client_id":   current_app.config["GITHUB_CLIENT_ID"],
        "redirect_uri": url_for("auth.oauth_github_callback", _external=True),
        "scope":       "user:email",
        "state":       state,
    }
    return redirect("https://github.com/login/oauth/authorize?" + urlencode(params))


@auth_bp.route("/oauth/github/callback")
def oauth_github_callback():
    code = request.args.get("code")
    token_resp = requests.post(
        "https://github.com/login/oauth/access_token",
        data={
            "client_id":     current_app.config["GITHUB_CLIENT_ID"],
            "client_secret": current_app.config["GITHUB_CLIENT_SECRET"],
            "code":          code,
        },
        headers={"Accept": "application/json"}
    ).json()

    access_token = token_resp.get("access_token")
    user_data = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()
    emails = requests.get(
        "https://api.github.com/user/emails",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()
    primary_email = next((e["email"] for e in emails if e["primary"]), None)

    return _handle_oauth_user(
        provider="github",
        provider_id=str(user_data.get("id")),
        email=primary_email,
        name=user_data.get("name") or user_data.get("login"),
        avatar=user_data.get("avatar_url"),
    )


def _handle_oauth_user(provider: str, provider_id: str, email: str, name: str, avatar: str):
    """Upsert OAuth user and log them in."""
    provider_field = f"{provider}_id"
    user = User.query.filter(getattr(User, provider_field) == provider_id).first()

    if not user and email:
        user = User.query.filter_by(email=email.lower()).first()

    if not user:
        base_username = (name or email.split("@")[0]).replace(" ", "_").lower()[:30]
        username = base_username
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{base_username}{counter}"
            counter += 1

        user = User(
            email=email.lower(), username=username, display_name=name,
            avatar_url=avatar, is_verified=True, is_active=True,
            oauth_provider=provider,
        )
        user.avatar_initials = user.generate_avatar_initials()

    setattr(user, provider_field, provider_id)
    db.session.add(user)
    db.session.commit()
    return _complete_login(user, remember=True)


# ──────────────────────────────────────────────────────────────
# ROUTES — 2FA SETUP
# ──────────────────────────────────────────────────────────────
@auth_bp.route("/settings/2fa/setup", methods=["GET", "POST"])
@login_required
def setup_2fa():
    if not current_user.totp_secret:
        current_user.generate_totp_secret()
        db.session.commit()

    qr_uri = current_user.get_totp_uri()
    import qrcode, io, base64
    qr = qrcode.QRCode(box_size=8)
    qr.add_data(qr_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    if request.method == "POST":
        token = request.form.get("token")
        if current_user.verify_totp(token):
            current_user.is_2fa_enabled = True
            db.session.commit()
            flash("2FA enabled successfully!", "success")
            return redirect(url_for("auth.security_settings"))
        flash("Invalid token.", "danger")

    return render_template("auth/setup_2fa.html", qr_b64=qr_b64, secret=current_user.totp_secret)


@auth_bp.route("/settings/2fa/disable", methods=["POST"])
@login_required
def disable_2fa():
    token = request.form.get("token")
    if current_user.verify_totp(token):
        current_user.is_2fa_enabled = False
        current_user.totp_secret = None
        db.session.commit()
        flash("2FA disabled.", "warning")
    else:
        flash("Invalid TOTP code.", "danger")
    return redirect(url_for("auth.security_settings"))


# ──────────────────────────────────────────────────────────────
# ROUTES — SESSION MANAGEMENT
# ──────────────────────────────────────────────────────────────
@auth_bp.route("/sessions")
@login_required
def active_sessions():
    sessions = UserSession.query.filter_by(
        user_id=current_user.id, is_active=True
    ).order_by(UserSession.last_seen_at.desc()).all()
    return render_template("auth/sessions.html", sessions=sessions)


@auth_bp.route("/sessions/<int:session_id>/revoke", methods=["POST"])
@login_required
def revoke_session(session_id: int):
    sess = UserSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    sess.revoke()
    db.session.commit()
    flash("Session revoked.", "success")
    return redirect(url_for("auth.active_sessions"))


