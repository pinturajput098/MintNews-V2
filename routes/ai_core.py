from flask import Blueprint, jsonify, request
from extensions import db
from models import NewsArticle
import requests
import os

ai_bp = Blueprint('ai_bp', __name__)

def query_gemini_bulletproof(prompt):
    """Queries Google Gemini production endpoints with intelligent rate-limit tracking"""
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return {"error": "GEMINI_API_KEY is missing in Render Environment Settings."}

    no_proxies = {
        "http": None,
        "https": None
    }

    # 🚀 Prioritizing the absolute stable production layouts
    test_matrix = [
        ("v1", "gemini-2.0-flash"),
        ("v1beta", "gemini-2.0-flash"),
        ("v1beta", "gemini-1.5-pro")
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

    errors = []
    for version, model in test_matrix:
        try:
            url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent?key={api_key}"
            response = requests.post(url, json=payload, proxies=no_proxies, timeout=12)
            res_data = response.json()
            
            if 'candidates' in res_data and len(res_data['candidates']) > 0:
                text = res_data['candidates'][0]['content']['parts'][0]['text']
                return {"success": True, "text": text}
            
            if 'error' in res_data:
                err_msg = res_data['error'].get('message', '')
                status = res_data['error'].get('status', '')
                
                # 🛑 CRITICAL FIX: If Google says rate limit is hit, alert the user directly instead of failing silently
                if status == "RESOURCE_EXHAUSTED" or "quota" in err_msg.lower():
                    return {"error": "Google Free Tier Rate Limit Hit (15 RPM). Please wait 30 seconds and try again!"}
                
                errors.append(f"{model}({version}): {err_msg}")
        except Exception as e:
            errors.append(f"{model}({version}): {str(e)}")
            continue
            
    return {"error": " | ".join(errors)}

@ai_bp.route('/process-article', methods=['POST'])
def process_article():
    data = request.get_json() or {}
    article_id = data.get('article_id')
    operation_type = data.get('operation')
    target_lang = data.get('language', 'English')
    
    article = NewsArticle.query.get(int(article_id))
    if not article:
        return jsonify({'result': 'Error: News article target reference missing.'})

    prompt = f"Perform operation '{operation_type}' on this news article text. Respond extensively and beautifully in fluid {target_lang}. Content: {article.content}"
    
    result = query_gemini_bulletproof(prompt)
    if "success" in result:
        return jsonify({'status': 'success', 'result': result["text"]})
    else:
        return jsonify({'result': f"Gemini Direct Error: {result['error']}"})

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
