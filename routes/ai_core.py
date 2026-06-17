from flask import Blueprint, jsonify, request
from extensions import db
from models import NewsArticle
import requests
import os

ai_bp = Blueprint('ai_bp', __name__)

def query_gemini_bulletproof(prompt):
    """Queries Google Gemini API directly via pure HTTP requests bypassing all proxy blocks"""
    # First priority: GEMINI_API_KEY variable from Render settings
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return {"error": "GEMINI_API_KEY is missing in Render Environment Settings."}

    # 🔒 Force bypass any broken Render internal network proxies
    no_proxies = {
        "http": None,
        "https": None
    }

    # Official Google Core Global Endpoint (100% DNS Uptime)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.5,
            "maxOutputTokens": 800
        }
    }

    try:
        response = requests.post(url, json=payload, proxies=no_proxies, timeout=15)
        res_data = response.json()
        
        if 'candidates' in res_data and len(res_data['candidates']) > 0:
            text = res_data['candidates'][0]['content']['parts'][0]['text']
            return {"success": True, "text": text}
        elif 'error' in res_data:
            return {"error": res_data['error'].get('message', str(res_data))}
        else:
            return {"error": f"Unexpected structural response: {str(res_data)}"}
    except Exception as e:
        return {"error": f"Google Core Gateway Connection Timeout: {str(e)}"}

@ai_bp.route('/process-article', methods=['POST'])
def process_article():
    data = request.get_json() or {}
    article_id = data.get('article_id')
    operation_type = data.get('operation')
    target_lang = data.get('language', 'English')
    
    article = NewsArticle.query.get(int(article_id))
    if not article:
        return jsonify({'result': 'Error: Target article index missing.'})

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
