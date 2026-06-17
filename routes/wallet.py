from flask import Blueprint, jsonify, request
from extensions import db, limiter
from models import User, AdWatchLog
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

wallet_bp = Blueprint('wallet_bp', __name__)

# ==============================================================================
# ROUTE 1: LOG AND VALIDATE WATCHED ADS (EARN CREDITS)
# ==============================================================================
@wallet_bp.route('/watch-ad', methods=['POST'])
@jwt_required()
@limiter.limit("20 per hour")
def watch_ad():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if not user:
        return jsonify({'error': 'User tracking matrix unassigned'}), 404
        
    # Standard designated premium monetization link mapping
    target_ad_url = "https://omg10.com/4/11162641"
    
    # Process wallet credit allocation transactions safely
    user.ad_credits += 1
    
    # Store complete telemetry trace auditing for fraud prevention
    log_entry = AdWatchLog(
        user_id=user.id,
        monetized_ad_url=target_ad_url,
        credited_amount=1
    )
    
    db.session.add(log_entry)
    db.session.commit()
    
    return jsonify({
        'message': 'Ad verification logged successfully. 1 Credit aggregated.',
        'current_credits': user.ad_credits,
        'verified_ad_target': target_ad_url
    }), 200

# ==============================================================================
# ROUTE 2: CLAIM SUBSCRIPTION PACKS WITH ACCUMULATED CREDITS
# ==============================================================================
@wallet_bp.route('/claim-subscription', methods=['POST'])
@jwt_required()
@limiter.limit("5 per minute")
def claim_subscription():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if not user:
        return jsonify({'error': 'User authentication token mismatch'}), 404
        
    data = request.get_json() or {}
    plan_days = data.get('plan') # Accepted parameters: 1, 3, 7, 28
    
    # Core system rule definition matching strict database architecture requirements
    plan_matrix = {
        1:  {"cost": 10,  "days_to_add": 1},
        3:  {"cost": 27,  "days_to_add": 3},
        7:  {"cost": 60,  "days_to_add": 7},
        28: {"cost": 250, "days_to_add": 28}
    }
    
    if plan_days not in plan_matrix:
        return jsonify({
            'error': 'Invalid premium bundle allocation matrix selection',
            'supported_plans': 'Choose from 1 day (10 credits), 3 days (27 credits), 7 days (60 credits), or 28 days (250 credits)'
        }), 400
        
    selected_plan = plan_matrix[plan_days]
    required_cost = selected_plan["cost"]
    days_to_grant = selected_plan["days_to_add"]
    
    # Verify account balance safety barriers
    if user.ad_credits < required_cost:
        return jsonify({
            'error': 'Insufficient Ad credits balance',
            'credits_required': required_cost,
            'current_balance': user.ad_credits,
            'credits_short': required_cost - user.ad_credits
        }), 402
        
    # Execute transactional deduction matrices
    user.ad_credits -= required_cost
    
    # Calculate non-overlapping subscription expiry timestamps
    time_now = datetime.utcnow()
    if user.subscription_expiry and user.subscription_expiry > time_now:
        # User has an active package, append additional days to current timestamp string safely
        user.subscription_expiry += timedelta(days=days_to_grant)
    else:
        # User is completely fresh or expired, trigger timestamp initiation immediately
        user.subscription_expiry = time_now + timedelta(days=days_to_grant)
        
    db.session.commit()
    
    return jsonify({
        'message': f'Premium tier activated successfully for {days_to_grant} days!',
        'wallet_remaining_credits': user.ad_credits,
        'subscription_expiry_timestamp': user.subscription_expiry.isoformat(),
        'premium_active': user.is_premium_active,
        'days_remaining': user.remaining_premium_days
    }), 200

# ==============================================================================
# ROUTE 3: WALLET ACCOUNT METRICS DASHBOARD
# ==============================================================================
@wallet_bp.route('/balance-telemetry', methods=['GET'])
@jwt_required()
def balance_telemetry():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if not user:
        return jsonify({'error': 'Invalid access context mapping parameters'}), 404
        
    return jsonify({
        'username': user.username,
        'ad_credits_balance': user.ad_credits,
        'premium_status_active': user.is_premium_active,
        'total_days_remaining': user.remaining_premium_days,
        'expiry_date': user.subscription_expiry.isoformat() if user.subscription_expiry else None,
        'user_tier': 'PREMIUM_ELITE_MEMBER' if user.is_premium_active else 'FREE_AGGREGATOR_LIMITS'
    }), 200
