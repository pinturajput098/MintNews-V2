from flask import Blueprint, jsonify, request
from extensions import db
from models import NewsArticle
import requests
import os
import time

ai_bp = Blueprint('ai_bp', __name__)

def query_gemini_final(prompt):
    """Ultimate stable Google Gemini API gateway with smart recovery handles"""
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return {"error": "GEMINI_API_KEY is missing in Render Environment settings."}

    no_proxies = {"http": None, "https": None}
    
    # Absolute production stable endpoints
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.6,
            "maxOutputTokens": 800
        }
    }

    # 🔄 Smart Retry: Agar rate limit hit bhi ho, toh code automatic thoda wait karke wapas chalega
    for attempt in range(2):
        try:
            response = requests.post(url, json=payload, proxies=no_proxies, timeout=12)
            res_data = response.json()
            
            if 'candidates' in res_data and len(res_data['candidates']) > 0:
                text = res_data['candidates'][0]['content']['parts'][0]['text']
                return {"success": True, "text": text}
            
            if 'error' in res_data:
                status = res_data['error'].get('status', '')
                if status == "RESOURCE_EXHAUSTED" and attempt == 0:
                    time.sleep(2)  # Cooldown wait step
                    continue
                return {"error": res_data['error'].get('message', str(res_data))}
                
        except Exception as e:
            if attempt == 0:
                continue
            return {"error": f"Network Error: {str(e)}"}
            
    return {"error": "Google Core engine busy. Try hitting the action again!"}

@ai_bp.route('/process-article', methods=['POST'])
def process_article():
    data = request.get_json() or {}
    article_id = data.get('article_id')
    operation_type = data.get('operation')
    target_lang = data.get('language', 'English')
    
    article = NewsArticle.query.get(int(article_id))
    if not article:
        return jsonify({'result': 'Error: Target article missing.'})

    prompt = f"Perform operation '{operation_type}' on this news article text. Respond comprehensively in {target_lang}. Content: {article.content}"
    
    result = query_gemini_final(prompt)
    if "success" in result:
        return jsonify({'status': 'success', 'result': result["text"]})
    else:
        return jsonify({'result': f"Gemini Error: {result['error']}"})

@ai_bp.route('/jarvis-chat', methods=['POST'])
def jarvis_chat():
    data = request.get_json() or {}
    user_prompt = data.get('prompt', '').strip()
    
    if not user_prompt:
        return jsonify({'response': 'Prompt query cannot be empty.'})

    prompt = f"You are Jarvis, the system core AI of MintNews V4. Help the user natively in fluid conversational Hinglish. User prompt: {user_prompt}"
    
    result = query_gemini_final(prompt)
    if "success" in result:
        return jsonify({'response': result["text"]})
    else:
        return jsonify({'response': f"Jarvis Error: {result['error']}"})
