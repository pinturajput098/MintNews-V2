from flask import Blueprint, jsonify, request
from extensions import db
from models import NewsArticle
import requests
import os

ai_bp = Blueprint('ai_bp', __name__)

@ai_bp.route('/process-article', methods=['POST'])
def process_article():
    data = request.get_json() or {}
    article_id = data.get('article_id')
    operation_type = data.get('operation')
    target_lang = data.get('language', 'English')
    
    article = NewsArticle.query.get(int(article_id))
    if not article:
        return jsonify({'result': 'Error: Target article not found in database.'})

    # 🌐 Native environment variable check
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        return jsonify({'result': 'Error: OPENROUTER_API_KEY missing in Render Settings.'})

    try:
        prompt = f"Perform operation '{operation_type}' on this news content. Respond comprehensively in {target_lang}. Content: {article.content}"
        
        # Pure HTTP request - No crashing SDK proxies argument bugs!
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta-llama/llama-3-8b-instruct:free",
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        res_data = response.json()
        
        if 'choices' in res_data and len(res_data['choices']) > 0:
            ai_text = res_data['choices'][0]['message']['content']
            return jsonify({'status': 'success', 'result': ai_text})
        else:
            return jsonify({'result': f"OpenRouter API Error: {str(res_data)}"})
            
    except Exception as e:
        return jsonify({'result': f"Critical Request Interface Error: {str(e)}"})

@ai_bp.route('/jarvis-chat', methods=['POST'])
def jarvis_chat():
    data = request.get_json() or {}
    user_prompt = data.get('prompt', '')
    
    if not user_prompt:
        return jsonify({'response': 'Prompt cannot be empty.'})

    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        return jsonify({'response': 'Error: OPENROUTER_API_KEY missing in Render environment variables.'})

    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta-llama/llama-3-8b-instruct:free",
            "messages": [
                {"role": "system", "content": "You are Jarvis, the core terminal engine of MintNews V4. Respond directly and smartly in conversational Hinglish."},
                {"role": "user", "content": user_prompt}
            ]
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        res_data = response.json()
        
        if 'choices' in res_data and len(res_data['choices']) > 0:
            return jsonify({'response': res_data['choices'][0]['message']['content']})
        else:
            return jsonify({'response': f"Jarvis Error Logs: {str(res_data)}"})
    except Exception as e:
        return jsonify({'response': f"Jarvis Connection Failure: {str(e)}"})
