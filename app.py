import os
import sys
from flask import Flask, jsonify, render_template, request
from extensions import db, socketio, jwt, limiter
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'nexus-v4-stealth-alpha-secret-string-99'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mintnews_v4.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = 'jwt-tokenization-matrix-secret-key'

    db.init_app(app)
    socketio.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)

    from routes.auth import auth_bp
    from routes.ai_core import ai_bp
    from routes.wallet import wallet_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')
    app.register_blueprint(wallet_bp, url_prefix='/api/wallet')

    with app.app_context():
        db.create_all()
        
        from models import NewsArticle
        # 🚀 SEEDER ENGINE OVERHAUL: GENERATES 100+ COGNITIVE STREAMS ACROSS ALL DISCRETE SECTIONS
        if NewsArticle.query.count() < 100:
            NewsArticle.query.delete() # Wipe clean for structural refresh
            
            categories_pool = ["General", "Forex", "Crypto", "Tech", "World"]
            image_pool = {
                "General": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=500&auto=format&fit=crop",
                "Forex": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=500&auto=format&fit=crop",
                "Crypto": "https://images.unsplash.com/photo-1516245834210-c4c142787335?w=500&auto=format&fit=crop",
                "Tech": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=500&auto=format&fit=crop",
                "World": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=500&auto=format&fit=crop"
            }
            
            titles_dict = {
                "General": ["Global Logistics Supply Chains Realignment Index Matrix", "Macroeconomic Shifts in Emerging Market Consumer Indicators"],
                "Forex": ["Federal Reserves Policy Adjustments Triggers Breakouts", "EURUSD Orderblock Convergence Near Key Liquidity Pool"],
                "Crypto": ["Bitcoin Whale Liquidation Sweeps Map Triggers Rally", "Ethereum Layer 2 Protocol Integration Speeds Telemetry"],
                "Tech": ["Asynchronous Compute Engines Scale Large Language Models", "Quantum Cryptography Keys Bypass Traditional Security Guards"],
                "World": ["Climate Resiliency Pacts Ratified in Global Summit Forum", "Geopolitical Energy Distribution Networks Re-Mapped Securely"]
            }

            counter = 1
            for cat in categories_pool:
                for i in range(25): # Injects 25 articles per section cleanly = 125 Total database assets
                    title_string = f"{titles_dict[cat][i % 2]} Alpha Series Node {counter}"
                    article = NewsArticle(
                        title=title_string,
                        slug=f"article-telemetry-reference-slug-{counter}",
                        content=f"Deep analytical structural tracing logs for {title_string}. Enterprise monitoring nodes capture extreme variance metrics within baseline data parameters. Quantitative indicators imply systemic trends consolidation.",
                        category=cat,
                        image_url=image_pool[cat],
                        original_source="Enterprise Central V4 Terminal Engine"
                    )
                    db.session.add(article)
                    counter += 1
            db.session.commit()

    @app.route('/')
    def index():
        from models import NewsArticle
        category_filter = request.args.get('category')
        search_query = request.args.get('q') # 🔍 SQL LIVE INPUT MATRIX HANDLER

        query = NewsArticle.query
        
        if category_filter and category_filter != "All":
            query = query.filter_by(category=category_filter)
            
        if search_query:
            query = query.filter(
                db.or_(
                    NewsArticle.title.like(f"%{search_query}%"),
                    NewsArticle.content.like(f"%{search_query}%")
                )
            )
            
        articles = query.order_by(NewsArticle.created_at.desc()).limit(100).all()
        categories_list = ["All", "General", "Forex", "Crypto", "Tech", "World"]
        
        return render_template(
            'base.html', 
            articles=articles, 
            categories=categories_list,
            current_category=category_filter or "All"
        )

    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 10000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
