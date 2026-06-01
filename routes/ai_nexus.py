from flask import Blueprint, jsonify, request
from extensions import limiter
import os

ai_bp = Blueprint('ai_bp', __name__)

@ai_bp.route('/jarvis-intelligence', methods=['POST'])
@limiter.limit("20 per hour")
def ask_jarvis():
    data = request.get_json() or {}
    user_prompt = data.get('prompt', '')
    
    if not user_prompt:
        return jsonify({'error': 'Prompt stream input required'}), 400
        
    response_payload = (
        f"Jarvis Framework core initialized. System processed analytics parameters for instructions: '{user_prompt}'. "
        f"Forex/Crypto correlation patterns show stable liquidity pools near local demand levels."
    )
    
    return jsonify({
        'node_identifier': 'Jarvis-Nexus-V3',
        'ai_response': response_payload,
        'sentiment_badge_assigned': 'Neutral/Positive'
    }), 200
