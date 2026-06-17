import os
import sys
import random
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
        # Force a database flush if records are duplicate or less than 100
        if NewsArticle.query.count() < 100:
            NewsArticle.query.delete()
            db.session.commit()
            
            categories_pool = ["General", "Forex", "Crypto", "Tech", "World"]
            image_pool = {
                "General": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=500&auto=format&fit=crop",
                "Forex": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=500&auto=format&fit=crop",
                "Crypto": "https://images.unsplash.com/photo-1516245834210-c4c142787335?w=500&auto=format&fit=crop",
                "Tech": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=500&auto=format&fit=crop",
                "World": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=500&auto=format&fit=crop"
            }
            
            # Combinatorial matrices to generate 100% distinct titles
            subjects = {
                "General": ["Global Market Index", "Inflation Telemetry", "Supply Chain Route", "Retail Core Metrics", "Trade Volume Settlement"],
                "Forex": ["EURUSD Orderblock", "GBPUSD Liquidity Sweep", "USDJPY Pivot Zone", "XAUUSD Major Resistance", "DXY Trend Line Break"],
                "Crypto": ["Bitcoin Whale Wallet", "Ethereum Layer-3 Scaling", "Solana Liquidation Map", "DeFi Core Protocol Run", "On-Chain Analytics Volume"],
                "Tech": ["Asynchronous LLM Processing", "Groq Hardware Accelerator", "Quantum Compute Matrix", "Stealth Neural Nodes", "Silicon Processing Node"],
                "World": ["Geopolitical Energy Supply", "Macro Sovereign Agreements", "Maritime Trade Route Corridors", "Cross-Border Settlement Standard", "Infrastructure Liquidity"]
            }
            
            actions = ["Surges Unexpectedly", "Collapses Near Local Demand", "Triggers Massive Volatility", "Stabilizes Inside Consolidation Triangle", "Breaks Multi-Year High Pattern"]
            contexts = ["Due to Sudden Institutional Order Matching.", "As Quantitative Trading Algorithms Activate Automatically.", "Spur-of-the-Moment Capital Rotation Triggers Outflow.", "Market Depth Analytics Registers Unusual Volume Spikes.", "Following High-Frequency Central Bank Policy Liquidity Swaps."]

            counter = 1
            time_tracker = datetime.utcnow()
            
            for cat in categories_pool:
                for idx in range(22): # 22 * 5 categories = 110 unique articles injected seamlessly
                    sub = random.choice(subjects[cat])
                    act = random.choice(actions)
                    ctx = random.choice(contexts)
                    
                    generated_title = f"{sub} {act} (Node Array-Alpha #{counter})"
                    generated_content = f"Deep technical intelligence monitoring stream logs regarding {generated_title}. {ctx} Risk managers suggest close oversight on high-liquidity zones as algorithmic execution nodes execute trade optimization directives across major network execution channels."
                    
                    # Deduct exactly 1 minute sequentially per record to simulate clean history stream timeline
                    creation_timestamp = time_tracker - timedelta(minutes=counter)
                    
                    article = NewsArticle(
                        title=generated_title,
                        slug=f"dynamic-v4-slug-mapping-telemetry-{counter}-{random.randint(1000,9999)}",
                        content=generated_content,
                        category=cat,
                        image_url=image_pool[cat],
                        original_source="MintNews V4 Terminal Core",
                        created_at=creation_timestamp
                    )
                    db.session.add(article)
                    counter += 1
            db.session.commit()
            print("--- ✅ SUCCESS: 110 unique dynamic news items initialized seamlessly at 1m gaps ---")

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
