import os
import sys
from flask import Flask, jsonify, render_template
from extensions import db, socketio, jwt, limiter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_app():
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-nexus-super-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///mintnews_v3.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-tokenization-secret-string')

    db.init_app(app)
    socketio.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)

    from routes.auth import auth_bp
    from routes.trading import trading_bp
    from routes.ai_nexus import ai_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(trading_bp, url_prefix='/trading')
    app.register_blueprint(ai_bp, url_prefix='/ai')

    @app.route('/')
    def index():
        from models import NewsArticle
        articles = NewsArticle.query.order_by(NewsArticle.created_at.desc()).limit(10).all()
        return render_template('base.html', articles=articles)

    @app.errorhandler(404)
    def system_not_found(e):
        return jsonify({'error': 'Endpoint not found within MintNews V3 infrastructure'}), 404

    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 10000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
