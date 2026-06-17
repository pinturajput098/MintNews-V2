import os
from datetime import datetime
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), default='Subscriber', nullable=False)
    
    # 💰 WALLET & ADVANCED DAILY ADS LIMITS LOGIC
    ad_credits = db.Column(db.Integer, default=0, nullable=False)
    subscription_expiry = db.Column(db.DateTime, nullable=True)
    
    # Strict 24h Lock metrics: Max 10 ads tracker
    daily_ad_count = db.Column(db.Integer, default=0, nullable=False)
    last_ad_watched_at = db.Column(db.DateTime, nullable=True)
    
    login_streak = db.Column(db.Integer, default=1, nullable=False)
    last_login = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_premium_active(self):
        if self.subscription_expiry and self.subscription_expiry > datetime.utcnow():
            return True
        return False

    @property
    def remaining_premium_days(self):
        if not self.is_premium_active:
            return 0
        delta = self.subscription_expiry - datetime.utcnow()
        return max(0, delta.days + 1)

class AdWatchLog(db.Model):
    __tablename__ = 'ad_watch_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    monetized_ad_url = db.Column(db.String(255), default='https://omg10.com/4/11162641', nullable=False)
    credited_amount = db.Column(db.Integer, default=1, nullable=False)
    watched_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class NewsArticle(db.Model):
    __tablename__ = 'news_articles'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    slug = db.Column(db.String(250), unique=True, nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True) # General, Forex, Crypto, Tech, World
    original_source = db.Column(db.String(100), default='GNews Hub', nullable=True)
    
    # 🖼️ DYNAMIC IMAGE CORRELATION MATRIX
    image_url = db.Column(db.String(500), nullable=True)
    
    # AI Modules Storage
    ai_summary_short = db.Column(db.Text, nullable=True)
    ai_tweet_content = db.Column(db.Text, nullable=True)
    ai_detailed_brief = db.Column(db.Text, nullable=True)
    ai_video_script = db.Column(db.Text, nullable=True)
    ai_blog_expansion = db.Column(db.Text, nullable=True)
    audio_file_path = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
