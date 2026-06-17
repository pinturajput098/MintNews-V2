import os
from datetime import datetime, timedelta
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

# ==============================================================================
# MODULE 1 & 5: USER IDENTIFICATION, SECURITY PROFILE & SUBSCRIPTION STATUS
# ==============================================================================
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), default='Subscriber', nullable=False) # Subscriber, Editor, Admin
    
    # 💰 WALLET & CREDIT MANAGEMENT MATRIX (MintNews V4 Standards)
    ad_credits = db.Column(db.Integer, default=0, nullable=False) # 10 Ads watched = 10 Credits
    subscription_expiry = db.Column(db.DateTime, nullable=True) # None means user is explicitly on FREE tier
    
    # Engagement Tracking Metrics
    login_streak = db.Column(db.Integer, default=1, nullable=False)
    last_login = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Passive relations bindings
    ad_watch_records = db.relationship('AdWatchLog', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        """Generates high security structural hash string for user authentication"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifies cleartext parameters against secure system hashes"""
        return check_password_hash(self.password_hash, password)

    @property
    def is_premium_active(self):
        """Returns verification token flag indicating if user is within valid paid limits"""
        if self.subscription_expiry and self.subscription_expiry > datetime.utcnow():
            return True
        return False

    @property
    def remaining_premium_days(self):
        """Computes structural delay parameters for display on user configuration card"""
        if not self.is_premium_active:
            return 0
        delta = self.subscription_expiry - datetime.utcnow()
        return max(0, delta.days + 1)


# ==============================================================================
# MODULE 6: AD MONETIZATION INTEGRATION & TRACKING TELEMETRY LOGS
# ==============================================================================
class AdWatchLog(db.Model):
    __tablename__ = 'ad_watch_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Target validation tracking for specific dynamic URL pools
    monetized_ad_url = db.Column(db.String(255), default='https://omg10.com/4/11162641', nullable=False)
    credited_amount = db.Column(db.Integer, default=1, nullable=False) # 1 credit allocated per verified check
    
    watched_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# ==============================================================================
# MODULE 3 & 4: NEWS AGGREGATION CONTENT ARCHITECTURE & GENERATED AI MATRIX
# ==============================================================================
class NewsArticle(db.Model):
    __tablename__ = 'news_articles'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    slug = db.Column(db.String(250), unique=True, nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True) # Forex, Crypto, Tech, World etc.
    original_source = db.Column(db.String(100), default='GNews Pipeline Proxy', nullable=True)
    
    # 🧠 GROQ ENGINE GENERATED CONTENT HOOKS (Fully Modular Content Strings)
    ai_summary_short = db.Column(db.Text, nullable=True)   # Available on Free Tier
    ai_tweet_content = db.Column(db.Text, nullable=True)   # Available on Free Tier
    ai_detailed_brief = db.Column(db.Text, nullable=True)  # Premium Access Flag Required
    ai_video_script = db.Column(db.Text, nullable=True)    # Premium Access Flag Required
    ai_blog_expansion = db.Column(db.Text, nullable=True)  # Premium Access Flag Required
    
    # 🔊 ELEVENLABS VOICE COMPILING PATH
    audio_file_path = db.Column(db.String(255), nullable=True) # Premium Access Flag Required
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
