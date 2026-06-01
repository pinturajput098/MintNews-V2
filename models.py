import os
from datetime import datetime
from extensions import db

# ==============================================================================
# MODULE 1: AUTHENTICATION, SECURITY & USER ENGINE
# ==============================================================================
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    
    # RBAC (Role Based Access Control Hierarchy)
    role = db.Column(db.String(30), default='Subscriber', nullable=False) # Anonymous, Subscriber, Pro Trader, Editor, Admin
    
    # 2FA & Multi-tier Security Layers
    totp_secret = db.Column(db.String(100), nullable=True)
    fallback_key_encrypted = db.Column(db.Text, nullable=True)
    is_account_locked = db.Column(db.Boolean, default=False, nullable=False)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    device_fingerprint_hash = db.Column(db.String(100), nullable=True)
    
    # MODULE 6: COMPREHENSIVE GAMIFICATION METRICS
    mint_coins = db.Column(db.Float, default=100.0, nullable=False)
    experience_points = db.Column(db.Integer, default=0, nullable=False)
    level = db.Column(db.Integer, default=1, nullable=False)
    login_streak = db.Column(db.Integer, default=1, nullable=False)
    
    # Performance Telemetry
    last_login = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    trades = db.relationship('TradingJournal', backref='trader', lazy=True, cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='author', lazy=True, cascade="all, delete-orphan")
    wagers = db.relationship('PredictionWager', backref='wagerer', lazy=True, cascade="all, delete-orphan")


# ==============================================================================
# MODULE 2: FOREX & CRYPTO TRADING METRICS HUB
# ==============================================================================
class TradingJournal(db.Model):
    __tablename__ = 'trading_journals'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    pair = db.Column(db.String(20), nullable=False, index=True) # BTCUSD, EURUSD, XAUUSD
    trade_type = db.Column(db.String(10), nullable=False) # BUY, SELL
    position_size_lots = db.Column(db.Float, default=0.1, nullable=False)
    
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float, nullable=True)
    pnl = db.Column(db.Float, default=0.0, nullable=False)
    status = db.Column(db.String(20), default='OPEN', nullable=False) # OPEN, CLOSED
    
    trade_notes = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# ==============================================================================
# MODULE 3 & 4: ADVANCED NEWS ENGINE & NEXUS DEEP GEMINI AI DATA LAYERS
# ==============================================================================
class NewsArticle(db.Model):
    __tablename__ = 'news_articles'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    slug = db.Column(db.String(250), unique=True, nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True) # Forex, Crypto, India, World, Tech
    
    # Advanced Content Fields
    original_source_url = db.Column(db.String(500), nullable=True)
    read_time_minutes = db.Column(db.Integer, default=1, nullable=False)
    unique_views_count = db.Column(db.Integer, default=0, nullable=False)
    
    # AI Nexus Pipeline Telemetry Attributes
    ai_summary = db.Column(db.Text, nullable=True)
    sentiment_score_badge = db.Column(db.String(30), default='Neutral', nullable=False) # Positive, Negative, Neutral
    clickbait_index_rating = db.Column(db.Float, default=0.0, nullable=False) # Scale 0 - 100%
    automated_tags = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    article_comments = db.relationship('Comment', backref='article', lazy=True, cascade="all, delete-orphan")


# ==============================================================================
# MODULE 5: ENGAGEMENT & COMMUNITY SYSTEMS
# ==============================================================================
class Comment(db.Model):
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey('news_articles.id'), nullable=False)
    
    comment_text = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True) # Self-referencing node for nested strings
    
    upvotes = db.Column(db.Integer, default=0, nullable=False)
    downvotes = db.Column(db.Integer, default=0, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# ==============================================================================
# MODULE 6: COMPREHENSIVE PREDICTION MARKET METRICS
# ==============================================================================
class PredictionMarket(db.Model):
    __tablename__ = 'prediction_markets'
    
    id = db.Column(db.Integer, primary_key=True)
    challenge_question = db.Column(db.String(255), nullable=False) # e.g., "Will BTC hit $100k this week?"
    target_asset = db.Column(db.String(20), nullable=False) # BTCUSD, etc.
    
    total_wagered_credits = db.Column(db.Float, default=0.0, nullable=False)
    market_status = db.Column(db.String(20), default='ACTIVE', nullable=False) # ACTIVE, RESOLVED, EXPIRED
    correct_outcome_resolution = db.Column(db.String(20), nullable=True) # YES, NO
    
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    wagers = db.relationship('PredictionWager', backref='market', lazy=True, cascade="all, delete-orphan")


class PredictionWager(db.Model):
    __tablename__ = 'prediction_wagers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    market_id = db.Column(db.Integer, db.ForeignKey('prediction_markets.id'), nullable=False)
    
    selected_outcome = db.Column(db.String(20), nullable=False) # YES, NO
    wager_amount_coins = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# ==============================================================================
# MODULE 7: MONETIZATION & INVOICE MANAGEMENT PIPELINES
# ==============================================================================
class FinancialTransaction(db.Model):
    __tablename__ = 'financial_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    purchased_tier_plan = db.Column(db.String(50), nullable=False) # Premium Content, Alpha Trading Alerts
    paid_amount_fiat = db.Column(db.Float, nullable=False)
    gateway_reference_id = db.Column(db.String(100), unique=True, nullable=False) # Stripe / Razorpay Mock traces
    transaction_status = db.Column(db.String(20), default='COMPLETED', nullable=False) # COMPLETED, FAILED
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
