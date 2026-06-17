import os
import sys
from flask import Flask, jsonify, render_template, request
from extensions import db, socketio, jwt, limiter
from datetime import datetime, timedelta

# Enforce strict system root paths mapping for rendering Linux container stability
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_app():
    app = Flask(__name__)
    
    # 🌐 ENTERPRISE PRODUCTION CONFIGURATIONS (Render Friendly)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'nexus-v4-stealth-alpha-secret-string-99')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///mintnews_v4.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-tokenization-matrix-secret-key')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7) # Long life session tracking for mobile viewport wrappers

    # Bind active core extensions into application instance context
    db.init_app(app)
    socketio.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)

    # 🔄 REGISTER FLASK BLUEPRINT ARCHITECTURES SYSTEMATICALLY
    from routes.auth import auth_bp
    from routes.ai_core import ai_bp
    from routes.wallet import wallet_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')
    app.register_blueprint(wallet_bp, url_prefix='/api/wallet')

    # 💾 AUTOMATED LIVE DATA SCHEMAS CREATION & SEEDING ENGINE
    with app.app_context():
        db.create_all()
        
        # Self-healing seeder: If rows count is zero, inject premium mock streams instantly
        from models import NewsArticle
        if NewsArticle.query.count() == 0:
            mock_feeds = [
                {
                    "title": "Fed Rates Hold Steady: Global Market Liquidity Braces for Volatility Spikes",
                    "slug": "fed-rates-hold-steady-global-markets-2026",
                    "content": "The Federal Reserve has officially declared a pause on policy changes, sustaining baseline interest targets. Institutional orderblocks show high-volume defensive liquidity sweeps forming around major currency pairs like EURUSD and XAUUSD, signaling imminent macro breakouts.",
                    "category": "Forex",
                    "original_source": "Marketaux Hub Feed"
                },
                {
                    "title": "Bitcoin Whales Accumulate Near Local Orderblocks as Liquidation Map Flattens",
                    "slug": "bitcoin-whales-accumulate-liquidation-heatmaps",
                    "content": "On-chain analytics monitors indicate massive token movements from centralized exchanges directly into deep cold storage nodes. Market depth simulators register intense order clustering, indicating that algorithmic trend models are priming for a comprehensive crypto rally.",
                    "category": "Crypto",
                    "original_source": "GNews Pipeline Node"
                },
                {
                    "title": "Next-Gen Asynchronous AI Architectures Replace Outdated Static LLM Frameworks",
                    "slug": "next-gen-async-ai-architectures-groq-models",
                    "content": "High-frequency compute environments are implementing extreme optimization pipelines that bypass traditional latency barriers. Modern frameworks are leaning heavily on lightning-fast processors like Groq to deliver contextual real-time data streams globally at zero cost parameters.",
                    "category": "Tech",
                    "original_source": "TechCrunch Aggregator Shell"
                }
            ]
            
            for item in mock_feeds:
                article = NewsArticle(
                    title=item["title"],
                    slug=item["slug"],
                    content=item["content"],
                    category=item["category"],
                    original_source=item["original_source"]
                )
                db.session.add(article)
            db.session.commit()
            print("--- 🟢 SUCCESS: Database tables drawn and seed data injected smoothly! ---")

    # ==============================================================================
    # CORE ROUTE: MAIN FEED VIEW GATEWAY
    # ==============================================================================
    @app.route('/')
    @limiter.limit("60 per minute")
    def index():
        """Aggregates and returns top 100 structured trending articles sorted chronologically"""
        from models import NewsArticle
        category_filter = request.args.get('category')
        
        query = NewsArticle.query
        if category_filter:
            query = query.filter_by(category=category_filter)
            
        articles = query.order_by(NewsArticle.created_at.desc()).limit(100).all()
        
        # Formulate active category tabs for view toggles matrix control
        categories_list = ["All", "Forex", "Crypto", "Tech", "World", "Business", "Startups"]
        
        return render_template(
            'base.html', 
            articles=articles, 
            categories=categories_list,
            current_category=category_filter or "All"
        )

    # ==============================================================================
    # BACKEND TELEMETRY ERROR HANDLERS SYSTEM CONSOLE
    # ==============================================================================
    @app.errorhandler(404)
    def resource_not_found(e):
        return jsonify({
            'status': 'error',
            'code': 404,
            'message': 'Requested asset node path does not exist on MintNews V4 routing maps.'
        }), 404

    @app.errorhandler(500)
    def internal_system_failure(e):
        return jsonify({
            'status': 'critical_crash',
            'code': 500,
            'message': 'Internal telemetry pipeline anomaly detected. Threading structures operating safety fallback.',
            'traceback_log': 'Context layers isolated safely'
        }), 500

    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 10000))
    # Native pure asynchronous threading execution eliminates container thread deadlocks natively
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=port, 
        debug=False, 
        allow_unsafe_werkzeug=True
    )
