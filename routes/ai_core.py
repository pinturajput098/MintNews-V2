from flask import Blueprint, jsonify, request
from extensions import db
from models import NewsArticle
import requests
import os

ai_bp = Blueprint('ai_bp', __name__)

def query_gemini_bulletproof(prompt):
    """Queries Google Gemini API by brute-forcing active production and latest model route combinations"""
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return {"error": "GEMINI_API_KEY is missing in Render Environment Settings."}

    no_proxies = {
        "http": None,
        "https": None
    }

    # 🚀 Exhaustive matrix of EVERY possible working API version and model identifier combinations
    test_matrix = [
        ("v1", "gemini-2.0-flash"),
        ("v1beta", "gemini-2.0-flash"),
        ("v1", "gemini-1.5-flash"),
        ("v1beta", "gemini-1.5-flash-latest"),
        ("v1beta", "gemini-1.5-flash")
    ]
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.5,
            "maxOutputTokens": 800
        }
    }

    last_error_log = ""
    for version, model in test_matrix:
        try:
            url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent?key={api_key}"
            response = requests.post(url, json=payload, proxies=no_proxies, timeout=10)
            res_data = response.json()
            
            if 'candidates' in res_data and len(res_data['candidates']) > 0:
                text = res_data['candidates'][0]['content']['parts'][0]['text']
                return {"success": True, "text": text}
            elif 'error' in res_data:
                last_error_log = f"[{version}/{model}]: {res_data['error'].get('message', str(res_data))}"
        except Exception as e:
            last_error_log = f"[{version}/{model}]: {str(e)}"
            continue
            
    return {"error": f"All Google Matrix endpoints exhausted. Last Log: {last_error_log}"}

@ai_bp.route('/process-article', methods=['POST'])
def process_article():
    data = request.get_json() or {}
    article_id = data.get('article_id')
    operation_type = data.get('operation')
    target_lang = data.get('language', 'English')
    
    article = NewsArticle.query.get(int(article_id))
    if not article:
        return jsonify({'result': 'Error: Target article index node missing.'})

    prompt = f"Perform operation '{operation_type}' on this news article text. Respond extensively and beautifully in fluid {target_lang}. Content: {article.content}"
    
    result = query_gemini_bulletproof(prompt)
    if "success" in result:
        return jsonify({'status': 'success', 'result': result["text"]})
    else:
        return jsonify({'result': f"Gemini Matrix Error: {result['error']}"})

@ai_bp.route('/jarvis-chat', methods=['POST'])
def jarvis_chat():
    data = request.get_json() or {}
    user_prompt = data.get('prompt', '')
    
    if not user_prompt:
        return jsonify({'response': 'Prompt query cannot be empty.'})

    prompt = f"You are Jarvis, the highly advanced system core AI of MintNews V4. Help the user with an analytical response natively in conversational Hinglish. User prompt: {user_prompt}"
    
    result = query_gemini_bulletproof(prompt)
    if "success" in result:
        return jsonify({'response': result["text"]})
    else:
        return jsonify({'response': f"Jarvis Native Error: {result['error']}"})
