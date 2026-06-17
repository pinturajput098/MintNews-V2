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
        # Hard flush old repetitive identical template databases
        NewsArticle.query.delete()
        db.session.commit()
        
        print("--- 🛰️ LOADING MULTI-SOURCE LIVE INTERACTIVE NEWS SEEDER ---")
        
        gnews_token = "5b8559e3138b18090304c361c25653b0"
        marketaux_token = "YSU6oi4R1R0WahkqNdMWRUMyH5OPQSX8NuQ7nL3Y"
        
        base_time = datetime.utcnow()
        counter = 1
        seen_titles = set()

        # 🌐 SOURCE A: GNEWS ENGINE CHANNEL INTEGRATION
        try:
            gnews_endpoint = f"https://gnews.io/api/v4/top-headlines?category=general&lang=en&apikey={gnews_token}"
            gnews_data = requests.get(gnews_endpoint, timeout=4).json()
            if "articles" in gnews_data:
                for target in gnews_data["articles"]:
                    title_clean = target["title"]
                    if title_clean not in seen_titles:
                        seen_titles.add(title_clean)
                        db.session.add(NewsArticle(
                            title=title_clean,
                            slug=f"gnews-node-sync-v4-{counter}",
                            content=target["description"] or target["content"],
                            category="General" if counter % 2 == 0 else "World",
                            image_url=target["image"] or f"https://picsum.photos/600/400?random={counter}",
                            original_source=target["source"]["name"],
                            created_at=base_time - timedelta(minutes=counter * 2)
                        ))
                        counter += 1
        except Exception as e:
            print(f"GNews real-time extraction pipeline skipped: {e}")

        # 🌐 SOURCE B: MARKETAUX FOREX & MACRO LIQUIDITY ENGINE
        try:
            marketaux_endpoint = f"https://api.marketaux.com/v1/news/all?symbols=TSLA,AMZN,MSFT&filter_entities=true&api_token={marketaux_key}"
            m_data = requests.get(marketaux_endpoint, timeout=4).json()
            if "data" in m_data:
                for target in m_data["data"]:
                    title_clean = target["title"]
                    if title_clean not in seen_titles:
                        seen_titles.add(title_clean)
                        db.session.add(NewsArticle(
                            title=title_clean,
                            slug=f"marketaux-forex-sync-{counter}",
                            content=target["description"] or target["text"],
                            category="Forex",
                            image_url=target.get("image_url") or f"https://picsum.photos/600/400?random={counter + 50}",
                            original_source=target.get("source", "WallStreet Terminal"),
                            created_at=base_time - timedelta(minutes=counter * 3)
                        ))
                        counter += 1
        except Exception as e:
            print(f"Marketaux live macro array skipped: {e}")

        # ⚙️ SECURE HIGH-VARIETY REALISTIC FALLBACK STREAMS (Guarantees unique cards)
        fallback_titles = [
            ("Crypto", "SEC Approves Institutional Layer-1 Smart Contract Liquidity Frameworks", "Major financial regulatory bodies have cleared baseline operational limits for multi-chain decentralized finance systems globally."),
            ("Crypto", "Solana Network Architecture Experiences Massive Transaction Volume Surge", "On-chain transaction depth modules catch unprecedented volume spikes near historical demand blocks as capital rotation intensifies."),
            ("Tech", "NVIDIA Unveils Advanced Blackwell B300 Ultra AI Architecture Processors", "The computing sector registers hyper-scale computing leaps utilizing advanced neural hardware processing topologies to process real-time inference."),
            ("Tech", "OpenAI Injects Fully Autonomous Agent Runtimes Across Corporate Terminals", "Next-gen asynchronous models gain full capability optimization modules to run multi-threaded operational infrastructure configurations natively."),
            ("Forex", "DXY US Dollar Index Consolidates Inside Dense Orderblock Zones", "Technical charting metrics monitor structural trend stabilization patterns waiting for upcoming central banking liquidity allocation parameters."),
            ("World", "Global Energy Consortium Outlines Automated Cross-Border Energy Distribution Links", "Sovereign trade networks establish unified physical routing channels to optimize long-distance infrastructure parameters securely.")
        ]

        while counter <= 105:
            item = random.choice(fallback_titles)
            title_compiled = f"{item[1]} (Telemetry Array #{counter})"
            if title_compiled not in seen_titles:
                seen_titles.add(title_compiled)
                db.session.add(NewsArticle(
                    title=title_compiled,
                    slug=f"mintnews-core-vector-v4-{counter}",
                    content=f"{item[2]} Technical monitors record substantial shifts within decentralized indices while automated algorithms rebalance cross-border pipelines dynamically.",
                    category=item[0],
                    image_url=f"https://picsum.photos/600/400?random={counter + random.randint(1000, 9999)}",
                    original_source="MintNews Intelligence Network",
                    created_at=base_time - timedelta(minutes=counter * 5)
                ))
                counter += 1

        db.session.commit()
        print(f"--- ✅ TOTAL DISTINCT FEED MATRIX REPOSITORY LOADED: {NewsArticle.query.count()} NODES ---")

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
