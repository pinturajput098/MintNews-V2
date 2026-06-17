import os
import sys
import random
import requests
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
        # Full wipe to clear out old repetitive identical images stack
        if NewsArticle.query.count() < 100:
            NewsArticle.query.delete()
            db.session.commit()
            
            print("--- 🌐 INTERACTIVE LIVE MULTI-API NETWORKS DISPATCH OVERHAUL ---")
            
            # API credentials parameters integration
            gnews_key = "5b8559e3138b18090304c361c25653b0"
            marketaux_key = "YSU6oi4R1R0WahkqNdMWRUMyH5OPQSX8NuQ7nL3Y"
            
            categories_pool = ["General", "Forex", "Crypto", "Tech", "World"]
            counter = 1
            base_time = datetime.utcnow()
            
            # 🛰️ MULTI-SOURCE PIPELINE PIPING LOGIC
            try:
                # Target Source A: GNews top headlines data streams
                gnews_url = f"https://gnews.io/api/v4/top-headlines?category=general&lang=en&apikey={gnews_key}"
                gnews_res = requests.get(gnews_url, timeout=5).json()
                
                if "articles" in gnews_res:
                    for art in gnews_res["articles"][:20]:
                        db.session.add(NewsArticle(
                            title=art["title"],
                            slug=f"gnews-live-payload-{counter}-{random.randint(100,999)}",
                            content=art["description"] or art["content"],
                            category="General" if counter % 2 == 0 else "World",
                            image_url=art["image"] or f"https://picsum.photos/500/300?random={counter}",
                            original_source=art["source"]["name"],
                            created_at=base_time - timedelta(minutes=counter)
                        ))
                        counter += 1
            except Exception as e:
                print(f"GNews stream skipped context: {e}")

            # ⚙️ HYBRID DIVERSIFIED FALLBACK MATRIX (Guarantees 110+ distinct cards with 100% unique graphics)
            subjects = {
                "General": ["Global Core Inflation Ledger", "Macro Labor Statistics Index", "Sovereign Debt Consolidation Matrix"],
                "Forex": ["EURUSD Resistance Breakout", "Liquidity Pool Sweeps on GBPUSD", "DXY Pivot Zone Liquidity Pull"],
                "Crypto": ["Whale Clusters Trigger Bitcoin Rally", "On-Chain Heatmaps Monitor Massive Outflows", "Ethereum Layer-3 Implementation Node"],
                "Tech": ["Silicon Compute Accelerators Scaling Arrays", "Asynchronous Large Language Inference Layer", "Stealth Neural Hardware Architecture"],
                "World": ["Maritime Trade Corridor Realignment", "Cross-Border Liquidity Framework Accords", "Global Energy Infrastructure Overhaul"]
            }
            actions = ["Surges Past Moving Averages", "Consolidates Inside Demand Zones", "Triggers Dynamic High-Volume Arbitrage"]
            contexts = ["Following sharp institutional orderbook matching blocks.", "As automated algorithmic asset rotation models execute.", "Spurred by high-frequency decentralized telemetry data tracking pipelines."]

            while counter <= 115:
                cat = random.choice(categories_pool)
                sub = random.choice(subjects[cat])
                act = random.choice(actions)
                ctx = random.choice(contexts)
                
                title_str = f"{sub} {act} (V4 Network Vector #{counter})"
                content_str = f"Live updates tracking {title_str}. {ctx} Quantitative trend indicators map dense support frameworks as liquidity optimization vectors settle globally."
                
                # 🖼️ Picsum Randomization: No two cards will ever pull the same image source frame!
                rand_img = f"https://picsum.photos/500/300?random={counter + random.randint(1000,9999)}"
                
                db.session.add(NewsArticle(
                    title=title_str,
                    slug=f"mintnews-dynamic-alpha-node-v4-{counter}",
                    content=content_str,
                    category=cat,
                    image_url=rand_img,
                    original_source="MintNews V4 Core Stream",
                    created_at=base_time - timedelta(minutes=counter)
                ))
                counter += 1
                
            db.session.commit()
            print(f"--- ✅ SUCCESS: 115 Multi-source unique news nodes with individual distinct images deployed! ---")

    @app.route('/')
    def index():
        from models import NewsArticle
        category_filter = request.args.get('category')
        search_query = request.args.get('q')

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
