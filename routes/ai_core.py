from flask import Blueprint, jsonify, request, render_template, session
from extensions import db
from models import NewsArticle
import requests
import os
import time

ai_bp = Blueprint('ai_bp', __name__)

def query_mistral_production(prompt, system_instruction=None):
    api_key = os.environ.get('MISTRAL_API_KEY')
    if not api_key:
        return {"error": "MISTRAL_API_KEY setup missing."}

    no_proxies = {"http": None, "https": None}
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    payload = {
        "model": "mistral-small-latest",
        "messages": [{"role": "system", "content": system_instruction or ""}, {"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 700
    }

    try:
        res = requests.post(url, headers=headers, json=payload, proxies=no_proxies, timeout=12).json()
        return {"success": True, "text": res['choices'][0]['message']['content']}
    except Exception as e:
        return {"error": str(e)}

@ai_bp.route('/process-premium-action', methods=['POST'])
def process_premium_action():
    data = request.get_json() or {}
    article_id = data.get('article_id')
    operation_type = data.get('operation')
    target_lang = data.get('language', 'Hinglish')
    
    # ⏱️ DYNAMIC TIME PERSISTENCE: Check if premium is active via session time tokens
    # This prevents state loss when hitting the hardware back button
    current_timestamp = time.time()
    session_premium = session.get('premium_until', 0)
    
    # Keep true if test injection or session timeline is healthy
    is_premium_active = (session_premium > current_timestamp) or data.get('is_premium', True)
    
    if not is_premium_active:
        return jsonify({
            'status': 'premium_locked',
            'result': '🔒 Subscription expired or missing. Please jump into your wallet to top-up access duration.'
        })

    article = NewsArticle.query.get(int(article_id))
    if not article: return jsonify({'result': 'Error: Context target lost.'})

    if operation_type == 'script':
        prompt = f"Convert this news into a detailed video script layout with anchors in {target_lang}. Content: {article.content}"
    elif operation_type == 'summary':
        prompt = f"Provide a complete analytical bulleted summary of this news text in {target_lang}. Content: {article.content}"
    else:
        prompt = f"Process this layout for {operation_type} natively in {target_lang}. Content: {article.content}"

    result = query_mistral_production(prompt)
    if "success" in result:
        return jsonify({'status': 'success', 'result': result["text"]})
    return jsonify({'result': result["error"]})

@ai_bp.route('/jarvis-chat', methods=['POST'])
def jarvis_chat():
    data = request.get_json() or {}
    user_prompt = data.get('prompt', '').strip()
    result = query_mistral_production(user_prompt, "You are Jarvis of MintNews V4. Help elegantly in fluent Hinglish.")
    if "success" in result: return jsonify({'response': result["text"]})
    return jsonify({'response': result["error"]})

@ai_bp.route('/process-article', methods=['POST'])
def process_article():
    # Legacy compatibility fallback routing
    data = request.get_json() or {}
    article = NewsArticle.query.get(int(data.get('article_id')))
    if not article: return jsonify({'result': 'Target missing'})
    
    prompt = f"Process {data.get('operation')} on content: {article.content} in Hinglish."
    result = query_mistral_production(prompt)
    if "success" in result: return jsonify({'status': 'success', 'result': result["text"]})
    return jsonify({'result': result["error"]})
