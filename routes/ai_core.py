from flask import Blueprint, jsonify, request
from extensions import db, limiter
from models import User, NewsArticle
from flask_jwt_extended import jwt_required, get_jwt_identity
from groq import Groq
import os
from datetime import datetime

ai_bp = Blueprint('ai_bp', __name__)

def get_groq_client():
    api_key = os.environ.get('GROQ', 'ENVIRONMENT_VARIABLE_KEY_PROXY')
    return Groq(api_key=api_key)

@ai_bp.route('/process-article', methods=['POST'])
@jwt_required(optional=True)
def process_article():
    data = request.get_json() or {}
    article_id = data.get('article_id')
    operation_type = data.get('operation')
    target_lang = data.get('language', 'English')
    
    article = NewsArticle.query.get(int(article_id))
    if not article:
        return jsonify({'error': 'Article node missing'}), 404

    try:
        client = get_groq_client()
        prompt = f"Perform operation '{operation_type}' on this news article content. Reply natively in {target_lang}. Content: {article.content}"
        
        # 🚀 UPGRADED TO LATEST LIVE PRODUCTION HIGH-SPEED GEN-AI INFRASTRUCTURE MODEL
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-specdec",
            temperature=0.5
        )
        result_payload = chat_completion.choices[0].message.content
        return jsonify({'status': 'success', 'result': result_payload})
    except Exception as e:
        return jsonify({'error': 'AI processing model failure', 'details': str(e)}), 500

@ai_bp.route('/jarvis-chat', methods=['POST'])
@jwt_required(optional=True)
def jarvis_chat():
    data = request.get_json() or {}
    user_prompt = data.get('prompt', '')
    
    if not user_prompt:
        return jsonify({'error': 'Query stream cannot be unassigned'}), 400

    try:
        client = get_groq_client()
        # 🚀 UPGRADED MULTILINGUAL SYSTEM MATRIX CHAT CONSOLE ROUTER
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are Jarvis, the system engine of MintNews V4. Answer in fluid mixed Hindi/English (Hinglish) accurately."},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.3-70b-specdec",
            temperature=0.7
        )
        ai_response = chat_completion.choices[0].message.content
        return jsonify({'response': ai_response}), 200
    except Exception as e:
        return jsonify({'error': 'Jarvis core interface failure', 'details': str(e)}), 500
