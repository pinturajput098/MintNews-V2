from flask import Blueprint, jsonify, request
from extensions import db, limiter
from models import User, AdWatchLog
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

wallet_bp = Blueprint('wallet_bp', __name__)

@wallet_bp.route('/watch-ad', methods=['POST'])
@jwt_required(optional=True)
def watch_ad():
    current_identity = get_jwt_identity()
    user_id = int(current_identity) if current_identity else 1
    
    user = User.query.get(user_id)
    if not user:
        user = User(id=1, username="Piyush07")
        user.set_password("AlphaV4Secure")
        db.session.add(user)
        db.session.commit()

    time_now = datetime.utcnow()
    
    # Strict 24-Hour safety lock calculation nodes
    if user.last_ad_watched_at:
        time_elapsed = time_now - user.last_ad_watched_at
        if time_elapsed < timedelta(hours=24):
            if user.daily_ad_count >= 10:
                time_remaining = timedelta(hours=24) - time_elapsed
                hours, remainder = divmod(time_remaining.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                return jsonify({
                    'error': 'LIMIT_LOCKED',
                    'message': f'Daily limit exhausted. Max 10 ads per 24 hours. Lock expires in {hours}h {minutes}m.'
                }), 403
        else:
            user.daily_ad_count = 0

    user.ad_credits += 1
    user.daily_ad_count += 1
    user.last_ad_watched_at = time_now
    
    log_entry = AdWatchLog(user_id=user.id, credited_amount=1)
    db.session.add(log_entry)
    db.session.commit()
    
    return jsonify({
        'message': 'Credit transaction logged successfully.',
        'current_credits': user.ad_credits,
        'daily_count': user.daily_ad_count,
        'remaining_ads': max(0, 10 - user.daily_ad_count)
    }), 200

@wallet_bp.route('/claim-subscription', methods=['POST'])
@jwt_required(optional=True)
def claim_subscription():
    current_identity = get_jwt_identity()
    user_id = int(current_identity) if current_identity else 1
    user = User.query.get(user_id)
    
    data = request.get_json() or {}
    plan_days = data.get('plan')
    
    # 💳 COMPLETE ACCURATE MULTI-TIER PLAN CONFIGURATION MATRIX
    plan_matrix = {
        1:  {"cost": 10,  "days": 1},
        3:  {"cost": 27,  "days": 3},
        7:  {"cost": 60,  "days": 7},
        28: {"cost": 250, "days": 28}
    }
    
    if plan_days not in plan_matrix:
        return jsonify({'error': 'Invalid premium tier allocation selected'}), 400
        
    selected = plan_matrix[plan_days]
    if user.ad_credits < selected["cost"]:
        return jsonify({'error': 'INSUFFICIENT_CREDITS', 'required': selected["cost"]}), 402
        
    user.ad_credits -= selected["cost"]
    time_now = datetime.utcnow()
    if user.subscription_expiry and user.subscription_expiry > time_now:
        user.subscription_expiry += timedelta(days=selected["days"])
    else:
        user.subscription_expiry = time_now + timedelta(days=selected["days"])
        
    db.session.commit()
    return jsonify({
        'premium_active': True,
        'wallet_remaining_credits': user.ad_credits,
        'days_remaining': user.remaining_premium_days
    }), 200
