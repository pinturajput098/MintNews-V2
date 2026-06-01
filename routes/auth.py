from flask import Blueprint, jsonify, request
from extensions import db, limiter
from models import User
from flask_jwt_extended import create_access_token
from datetime import datetime

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    data = request.get_json() or {}
    username = data.get('username')
    email = data.get('email')
    
    if not username or not email:
        return jsonify({'error': 'Missing core registration parameters'}), 400
        
    if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
        return jsonify({'error': 'Identity token conflict. Username or Email already exists.'}), 409
        
    user = User(username=username, email=email, role='Subscriber')
    db.session.add(user)
    db.session.commit()
    return jsonify({
        'message': 'User verified and synchronized successfully',
        'user_id': user.id,
        'mint_coins': user.mint_coins
    }), 201

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    data = request.get_json() or {}
    username = data.get('username')
    
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'Access denied. Invalid credentials.'}), 401
        
    if user.is_account_locked:
        return jsonify({'error': 'Account locked due to security alerts'}), 423
        
    user.last_login = datetime.utcnow()
    user.login_streak += 1
    db.session.commit()
    
    token = create_access_token(identity=str(user.id))
    return jsonify({
        'access_token': token,
        'profile': {
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'mint_coins': user.mint_coins,
            'level': user.level
        }
    }), 200
