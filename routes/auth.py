from flask import Blueprint, jsonify, request
from extensions import db, limiter
from models import User
from flask_jwt_extended import create_access_token
from datetime import datetime

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/signup', methods=['POST'])
@limiter.limit("5 per minute")
def signup():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password parameters are mandatory'}), 400
        
    # Enforce strict unique username check execution
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({'error': 'Username already taken. Choose a unique identity identifier.'}), 409
        
    # Initialize fresh V4 user structure parameters cleanly
    user = User(username=username, role='Subscriber', ad_credits=0)
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'message': 'Account created successfully! Welcome to MintNews V4.',
        'username': user.username,
        'wallet_credits': user.ad_credits,
        'tier': 'FREE'
    }), 201

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Credentials stream parameters required'}), 400
        
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Access denied. Invalid username or password credentials.'}), 401
        
    # Process login streak validation telemetry parameters
    time_now = datetime.utcnow()
    if (time_now - user.last_login).days == 1:
        user.login_streak += 1
    elif (time_now - user.last_login).days > 1:
        user.login_streak = 1
        
    user.last_login = time_now
    db.session.commit()
    
    # Generate secure enterprise access session token mapped to identifier string
    token = create_access_token(identity=str(user.id))
    
    return jsonify({
        'access_token': token,
        'profile': {
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'ad_credits': user.ad_credits,
            'premium_active': user.is_premium_active,
            'remaining_days': user.remaining_premium_days,
            'streak': user.login_streak
        }
    }), 200
