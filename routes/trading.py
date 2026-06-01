from flask import Blueprint, jsonify, request
from extensions import db, limiter
from models import TradingJournal, User
from flask_jwt_extended import jwt_required, get_jwt_identity

trading_bp = Blueprint('trading_bp', __name__)

@trading_bp.route('/journal/log', methods=['POST'])
@jwt_required()
@limiter.limit("30 per hour")
def log_trade():
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    pair = data.get('pair')
    trade_type = data.get('trade_type')
    entry_price = data.get('entry_price')
    size = data.get('position_size', 0.1)
    
    if not pair or not trade_type or not entry_price:
        return jsonify({'error': 'Incomplete trade telemetry matrix configuration'}), 400
        
    trade = TradingJournal(
        user_id=int(user_id),
        pair=pair.upper(),
        trade_type=trade_type.upper(),
        position_size_lots=float(size),
        entry_price=float(entry_price),
        status='OPEN'
    )
    db.session.add(trade)
    db.session.commit()
    return jsonify({
        'message': 'Trade synchronized into journal execution system',
        'trade_id': trade.id
    }), 201

@trading_bp.route('/market-matrix', methods=['GET'])
def market_matrix():
    return jsonify({
        'status': 'operational',
        'tickers': {
            'BTCUSD': {'price': 68452.10, 'sentiment': 'Bullish', 'daily_change_pct': 2.4},
            'EURUSD': {'price': 1.08420, 'sentiment': 'Neutral', 'daily_change_pct': -0.1},
            'XAUUSD': {'price': 2341.80, 'sentiment': 'Bullish', 'daily_change_pct': 1.1}
        },
        'crypto_fear_greed_index': 72,
        'whale_alerts_telemetry': 'Active monitoring active on high-liquidity orderblocks'
    }), 200
