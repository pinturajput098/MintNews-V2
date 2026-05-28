"""
MintNews Network V3 — Unified Database Models
models/__init__.py — All SQLAlchemy ORM models
"""

from __future__ import annotations
import enum
import json
import uuid
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
import pyotp
from cryptography.fernet import Fernet
from flask import current_app
from flask_login import UserMixin
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, DateTime,
    ForeignKey, Enum, JSON, BigInteger, Index, UniqueConstraint,
    Table, event
)
from sqlalchemy.orm import relationship, validates, backref
from sqlalchemy.ext.hybrid import hybrid_property

from app import db

# ──────────────────────────────────────────────────────────────
# ENUMERATIONS
# ──────────────────────────────────────────────────────────────
class UserRole(str, enum.Enum):
    ANONYMOUS  = "anonymous"
    SUBSCRIBER = "subscriber"
    PRO_TRADER = "pro_trader"
    EDITOR     = "editor"
    ADMIN      = "admin"

class ArticleStatus(str, enum.Enum):
    DRAFT      = "draft"
    IN_REVIEW  = "in_review"
    APPROVED   = "approved"
    PUBLISHED  = "published"
    ARCHIVED   = "archived"
    REJECTED   = "rejected"

class SentimentLabel(str, enum.Enum):
    VERY_BULLISH = "very_bullish"
    BULLISH      = "bullish"
    NEUTRAL      = "neutral"
    BEARISH      = "bearish"
    VERY_BEARISH = "very_bearish"

class TransactionType(str, enum.Enum):
    SUBSCRIPTION = "subscription"
    TIP          = "tip"
    REFUND       = "refund"
    PAYOUT       = "payout"
    CRYPTO       = "crypto"

class NotificationChannel(str, enum.Enum):
    EMAIL   = "email"
    PUSH    = "push"
    IN_APP  = "in_app"
    SMS     = "sms"

class TradeDirection(str, enum.Enum):
    LONG  = "long"
    SHORT = "short"

class AlertCondition(str, enum.Enum):
    ABOVE    = "above"
    BELOW    = "below"
    PERCENT_CHANGE = "percent_change"


# ──────────────────────────────────────────────────────────────
# ASSOCIATION TABLES
# ──────────────────────────────────────────────────────────────
user_followers = Table(
    "user_followers",
    db.Model.metadata,
    Column("follower_id",  Integer, ForeignKey("users.id"), primary_key=True),
    Column("following_id", Integer, ForeignKey("users.id"), primary_key=True),
)

article_tags = Table(
    "article_tags",
    db.Model.metadata,
    Column("article_id", Integer, ForeignKey("articles.id"), primary_key=True),
    Column("tag_id",     Integer, ForeignKey("tags.id"),      primary_key=True),
)

user_badges = Table(
    "user_badges",
    db.Model.metadata,
    Column("user_id",  Integer, ForeignKey("users.id"),  primary_key=True),
    Column("badge_id", Integer, ForeignKey("badges.id"), primary_key=True),
    Column("earned_at", DateTime, default=lambda: datetime.now(timezone.utc)),
)


# ──────────────────────────────────────────────────────────────
# MODULE 1: USER MODEL
# ──────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id               = Column(Integer,     primary_key=True)
    uuid             = Column(String(36),  unique=True, default=lambda: str(uuid.uuid4()), nullable=False)
    username         = Column(String(50),  unique=True, nullable=False, index=True)
    email            = Column(String(255), unique=True, nullable=False, index=True)
    _password_hash   = Column("password_hash", String(255))
    role             = Column(Enum(UserRole), default=UserRole.SUBSCRIBER, nullable=False)

    # Profile
    display_name     = Column(String(100))
    bio              = Column(Text)
    avatar_url       = Column(String(500))
    avatar_initials  = Column(String(4))   # Fallback generated avatar
    cover_image_url  = Column(String(500))
    website_url      = Column(String(255))
    twitter_handle   = Column(String(100))
    telegram_handle  = Column(String(100))
    location         = Column(String(100))
    timezone         = Column(String(50),  default="UTC")
    language         = Column(String(10),  default="en")
    theme            = Column(String(30),  default="dark")

    # Auth State
    is_active        = Column(Boolean, default=True,  nullable=False)
    is_verified      = Column(Boolean, default=False, nullable=False)
    is_2fa_enabled   = Column(Boolean, default=False)
    totp_secret      = Column(String(64))
    magic_link_token = Column(String(128))
    magic_link_expiry= Column(DateTime)
    recovery_key     = Column(String(128), unique=True, default=lambda: secrets.token_urlsafe(32))
    failed_logins    = Column(Integer, default=0)
    locked_until     = Column(DateTime)
    verification_token = Column(String(128))

    # OAuth
    google_id        = Column(String(100), unique=True)
    github_id        = Column(String(100), unique=True)
    apple_id         = Column(String(100), unique=True)
    oauth_provider   = Column(String(30))

    # Gamification
    xp_total         = Column(Integer, default=0)
    xp_level         = Column(Integer, default=1)
    mintcoins        = Column(Integer, default=0)
    streak_days      = Column(Integer, default=0)
    streak_last_seen = Column(DateTime)
    reputation_score = Column(Float,   default=0.0)

    # Subscription
    subscription_tier = Column(String(20), default="free")
    subscription_expiry = Column(DateTime)
    paper_trade_balance = Column(Float, default=10000.0)

    # Trading
    trading_style    = Column(String(50))  # scalper, swing, position
    risk_tolerance   = Column(String(20))  # low, medium, high

    # GDPR
    gdpr_consent_at  = Column(DateTime)
    data_export_requested_at = Column(DateTime)
    deletion_requested_at    = Column(DateTime)

    # Encryption key per user for sensitive fields
    _enc_key         = Column("enc_key", String(64), default=lambda: Fernet.generate_key().decode())

    # Referral
    referral_code    = Column(String(20), unique=True, default=lambda: secrets.token_urlsafe(8))
    referred_by_id   = Column(Integer, ForeignKey("users.id"))

    # Timestamps
    created_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login_at    = Column(DateTime)
    last_login_ip    = Column(String(45))
    last_login_country = Column(String(100))
    last_login_device  = Column(String(200))

    # ── Relationships ─────────────────────────────────────────
    sessions         = relationship("UserSession",     back_populates="user", cascade="all, delete-orphan")
    articles         = relationship("Article",         back_populates="author")
    comments         = relationship("Comment",         back_populates="author", cascade="all, delete-orphan")
    notifications    = relationship("Notification",    back_populates="user",   cascade="all, delete-orphan")
    bookmarks        = relationship("Bookmark",        back_populates="user",   cascade="all, delete-orphan")
    price_alerts     = relationship("PriceAlert",      back_populates="user",   cascade="all, delete-orphan")
    trading_entries  = relationship("TradingJournal",  back_populates="user",   cascade="all, delete-orphan")
    transactions     = relationship("Transaction",     back_populates="user",   cascade="all, delete-orphan")
    reactions        = relationship("Reaction",        back_populates="user",   cascade="all, delete-orphan")
    messages_sent    = relationship("DirectMessage",   foreign_keys="DirectMessage.sender_id",   back_populates="sender")
    messages_recv    = relationship("DirectMessage",   foreign_keys="DirectMessage.receiver_id", back_populates="receiver")
    badges           = relationship("Badge",           secondary=user_badges, backref="users")
    followers        = relationship(
        "User", secondary=user_followers,
        primaryjoin=lambda: user_followers.c.following_id == User.id,
        secondaryjoin=lambda: user_followers.c.follower_id == User.id,
        backref="following"
    )
    poll_votes       = relationship("PollVote", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_user_email_role", "email", "role"),
    )

    # ── Password ──────────────────────────────────────────────
    def set_password(self, password: str):
        salt = bcrypt.gensalt(rounds=12)
        self._password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def check_password(self, password: str) -> bool:
        if not self._password_hash:
            return False
        return bcrypt.checkpw(password.encode("utf-8"), self._password_hash.encode("utf-8"))

    # ── TOTP / 2FA ────────────────────────────────────────────
    def generate_totp_secret(self) -> str:
        self.totp_secret = pyotp.random_base32()
        return self.totp_secret

    def verify_totp(self, token: str) -> bool:
        if not self.totp_secret:
            return False
        return pyotp.TOTP(self.totp_secret).verify(token, valid_window=1)

    def get_totp_uri(self) -> str:
        return pyotp.totp.TOTP(self.totp_secret).provisioning_uri(
            name=self.email, issuer_name="MintNews Network"
        )

    # ── Magic Link ────────────────────────────────────────────
    def generate_magic_link(self) -> str:
        token = secrets.token_urlsafe(48)
        self.magic_link_token  = token
        self.magic_link_expiry = datetime.now(timezone.utc) + timedelta(minutes=15)
        return token

    def verify_magic_link(self, token: str) -> bool:
        if self.magic_link_token != token:
            return False
        if datetime.now(timezone.utc) > self.magic_link_expiry:
            return False
        self.magic_link_token  = None
        self.magic_link_expiry = None
        return True

    # ── Account Locking ───────────────────────────────────────
    def record_failed_login(self):
        self.failed_logins += 1
        if self.failed_logins >= 5:
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)

    def reset_failed_logins(self):
        self.failed_logins = 0
        self.locked_until  = None

    @property
    def is_locked(self) -> bool:
        if self.locked_until and datetime.now(timezone.utc) < self.locked_until:
            return True
        if self.locked_until and datetime.now(timezone.utc) >= self.locked_until:
            self.locked_until  = None
            self.failed_logins = 0
        return False

    # ── Streaks ───────────────────────────────────────────────
    def check_and_update_streak(self):
        now = datetime.now(timezone.utc)
        if self.streak_last_seen:
            delta = (now.date() - self.streak_last_seen.date()).days
            if delta == 1:
                self.streak_days += 1
            elif delta > 1:
                self.streak_days = 1
        else:
            self.streak_days = 1
        self.streak_last_seen = now

    # ── XP & Leveling ─────────────────────────────────────────
    def add_xp(self, points: int):
        self.xp_total += points
        old_level = self.xp_level
        self.xp_level = self._calculate_level(self.xp_total)
        return self.xp_level > old_level  # True if leveled up

    @staticmethod
    def _calculate_level(xp: int) -> int:
        thresholds = [0, 100, 300, 700, 1500, 3000, 6000, 12000, 25000, 50000]
        for i, t in enumerate(reversed(thresholds)):
            if xp >= t:
                return len(thresholds) - i
        return 1

    @property
    def level_title(self) -> str:
        titles = {
            1: "Newbie", 2: "Reader", 3: "Explorer", 4: "Analyst",
            5: "Chartist", 6: "Trader", 7: "Strategist", 8: "Alpha Trader",
            9: "Market Sage", 10: "Legend"
        }
        return titles.get(self.xp_level, "Unknown")

    # ── Subscription ──────────────────────────────────────────
    @property
    def is_premium(self) -> bool:
        if not self.subscription_expiry:
            return self.subscription_tier in ("premium", "alpha")
        return (self.subscription_tier in ("premium", "alpha") and
                self.subscription_expiry > datetime.now(timezone.utc))

    # ── Avatar generation ─────────────────────────────────────
    def generate_avatar_initials(self) -> str:
        parts = (self.display_name or self.username).split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return (self.username[:2]).upper()

    # ── Permissions ───────────────────────────────────────────
    def can(self, permission: str) -> bool:
        perms = {
            UserRole.ADMIN:      ["read", "write", "edit", "delete", "admin", "moderate"],
            UserRole.EDITOR:     ["read", "write", "edit", "moderate"],
            UserRole.PRO_TRADER: ["read", "write", "trade", "premium_analytics"],
            UserRole.SUBSCRIBER: ["read", "write"],
            UserRole.ANONYMOUS:  ["read"],
        }
        return permission in perms.get(self.role, [])

    def to_dict(self, include_private: bool = False) -> dict:
        data = {
            "id": self.id, "uuid": self.uuid, "username": self.username,
            "display_name": self.display_name, "bio": self.bio,
            "avatar_url": self.avatar_url, "avatar_initials": self.avatar_initials,
            "role": self.role.value, "xp_level": self.xp_level,
            "level_title": self.level_title, "mintcoins": self.mintcoins,
            "streak_days": self.streak_days, "reputation_score": self.reputation_score,
            "is_premium": self.is_premium, "created_at": self.created_at.isoformat(),
        }
        if include_private:
            data.update({
                "email": self.email, "is_2fa_enabled": self.is_2fa_enabled,
                "subscription_tier": self.subscription_tier,
                "referral_code": self.referral_code,
            })
        return data

    def __repr__(self):
        return f"<User {self.username} [{self.role.value}]>"


class UserSession(db.Model):
    """Active session tracking for session management dashboard."""
    __tablename__ = "user_sessions"

    id           = Column(Integer,    primary_key=True)
    user_id      = Column(Integer,    ForeignKey("users.id"), nullable=False, index=True)
    session_token= Column(String(128),unique=True, nullable=False, default=lambda: secrets.token_urlsafe(32))
    ip_address   = Column(String(45))
    user_agent   = Column(String(500))
    device_type  = Column(String(50))
    browser      = Column(String(100))
    os           = Column(String(100))
    country      = Column(String(100))
    city         = Column(String(100))
    fingerprint  = Column(String(64))   # Device fingerprint hash
    is_active    = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at   = Column(DateTime)

    user = relationship("User", back_populates="sessions")

    def revoke(self):
        self.is_active = False


# ──────────────────────────────────────────────────────────────
# MODULE 3: CONTENT & ARTICLES
# ──────────────────────────────────────────────────────────────
class Category(db.Model):
    __tablename__ = "categories"

    id          = Column(Integer,    primary_key=True)
    name        = Column(String(100),unique=True, nullable=False)
    slug        = Column(String(100),unique=True, nullable=False, index=True)
    description = Column(Text)
    icon        = Column(String(50))   # Lucide icon name
    color       = Column(String(7))    # Hex color
    sort_order  = Column(Integer, default=0)
    is_active   = Column(Boolean, default=True)
    parent_id   = Column(Integer, ForeignKey("categories.id"))
    children    = relationship("Category", backref=backref("parent", remote_side=[id]))
    articles    = relationship("Article", back_populates="category")
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Category {self.name}>"


class Tag(db.Model):
    __tablename__ = "tags"
    id       = Column(Integer,   primary_key=True)
    name     = Column(String(80),unique=True, nullable=False)
    slug     = Column(String(80),unique=True, nullable=False, index=True)
    use_count= Column(Integer, default=0)


class Article(db.Model):
    __tablename__ = "articles"

    id              = Column(Integer,    primary_key=True)
    uuid            = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    title           = Column(String(512),nullable=False)
    slug            = Column(String(512),unique=True, nullable=False, index=True)
    summary         = Column(Text)
    content         = Column(Text)
    content_html    = Column(Text)       # Rendered HTML from rich editor
    image_url       = Column(String(1000))
    image_alt_text  = Column(String(500)) # AI-generated alt text
    source_url      = Column(String(1000))
    source_name     = Column(String(200))
    source_favicon  = Column(String(500))

    # Classification
    category_id     = Column(Integer, ForeignKey("categories.id"), index=True)
    language        = Column(String(10), default="en")
    country         = Column(String(10))
    is_featured     = Column(Boolean, default=False)
    is_sponsored    = Column(Boolean, default=False)
    is_breaking     = Column(Boolean, default=False)
    is_external     = Column(Boolean, default=True)  # RSS/API sourced
    is_ai_generated = Column(Boolean, default=False)

    # Workflow
    status          = Column(Enum(ArticleStatus), default=ArticleStatus.PUBLISHED, index=True)
    author_id       = Column(Integer, ForeignKey("users.id"))
    editor_id       = Column(Integer, ForeignKey("users.id"))
    reviewed_at     = Column(DateTime)
    published_at    = Column(DateTime, index=True)
    scheduled_at    = Column(DateTime)

    # AI Enrichment
    ai_summary_short = Column(Text)
    ai_summary_long  = Column(Text)
    ai_tldr          = Column(Text)
    sentiment        = Column(Enum(SentimentLabel))
    sentiment_score  = Column(Float)
    clickbait_score  = Column(Float)   # 0-1, higher = more clickbait
    fake_news_score  = Column(Float)   # 0-1, higher = more likely fake
    ai_tags          = Column(JSON)    # List of AI-assigned tags
    readability_score= Column(Float)
    read_time_minutes= Column(Integer)

    # SEO
    meta_title       = Column(String(70))
    meta_description = Column(String(160))
    og_image_url     = Column(String(1000))
    canonical_url    = Column(String(1000))
    old_slugs        = Column(JSON, default=list)  # Redirect map for changed slugs

    # Metrics
    views_count      = Column(BigInteger, default=0)
    unique_views     = Column(BigInteger, default=0)
    total_dwell_ms   = Column(BigInteger, default=0)  # Total milliseconds spent
    shares_count     = Column(Integer, default=0)
    bookmarks_count  = Column(Integer, default=0)

    # Audio
    audio_url        = Column(String(1000))  # ElevenLabs TTS

    # Deduplication
    content_hash     = Column(String(64), index=True)  # SHA256 of content

    # Translations
    translations     = Column(JSON, default=dict)  # {"hi": {"title": "...", "summary": "..."}}

    # Timestamps
    created_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    fetched_at       = Column(DateTime)  # When scraped from API

    # ── Relationships ─────────────────────────────────────────
    category    = relationship("Category", back_populates="articles")
    author      = relationship("User", foreign_keys=[author_id], back_populates="articles")
    editor      = relationship("User", foreign_keys=[editor_id])
    ta
