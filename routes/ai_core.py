from flask import Blueprint, jsonify, request, render_template
from extensions import db
from models import NewsArticle
import requests
import os

ai_bp = Blueprint('ai_bp', __name__)

def query_mistral_production(prompt, system_instruction=None):
    api_key = os.environ.get('MISTRAL_API_KEY')
    if not api_key:
        return {"error": "MISTRAL_API_KEY missing from environment setup."}

    no_proxies = {"http": None, "https": None}
    url = "https://api.mistral.ai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "mistral-small-latest",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 700
    }

    try:
        response = requests.post(url, headers=headers, json=payload, proxies=no_proxies, timeout=12)
        res_data = response.json()
        if 'choices' in res_data and len(res_data['choices']) > 0:
            return {"success": True, "text": res_data['choices'][0]['message']['content']}
        return {"error": "Mistral returned empty structural response layout."}
    except Exception as e:
        return {"error": str(e)}

# 🔄 LEGACY COMPATIBILITY ROUTE: Fixed so old frontend clicks instantly hit Mistral
@ai_bp.route('/process-article', methods=['POST'])
def process_article():
    data = request.get_json() or {}
    article_id = data.get('article_id')
    operation_type = data.get('operation') # 'script', 'summary', or 'detailed'
    target_lang = data.get('language', 'Hinglish')
    
    article = NewsArticle.query.get(int(article_id))
    if not article:
        return jsonify({'result': 'Error: Article context missing.'})

    if operation_type == 'script':
        prompt = f"Convert this news into a detailed video script layout with visual anchors in {target_lang}. Content: {article.content}"
    elif operation_type == 'summary':
        prompt = f"Generate a sharp, high-speed business analytical summary with pointers in {target_lang}. Content: {article.content}"
    elif operation_type in ['detailed', 'detailed-dive']:
        prompt = f"Provide an extensive, deeply researched analytical breakdown of this news article in {target_lang}. Content: {article.content}"
    else:
        prompt = f"Perform operation '{operation_type}' on this news text. Respond in {target_lang}. Content: {article.content}"

    result = query_mistral_production(prompt)
    if "success" in result:
        return jsonify({'status': 'success', 'result': result["text"]})
    else:
        return jsonify({'result': result["error"]})

# 👑 NEW SUBSCRIPTION GATEWAY: (Kept completely alive for future subscription panel tokens)
@ai_bp.route('/process-premium-action', methods=['POST'])
def process_premium_action():
    data = request.get_json() or {}
    article_id = data.get('article_id')
    operation_type = data.get('operation')
    target_lang = data.get('language', 'Hinglish')
    
    # Simple simulated premium check
    is_user_premium = data.get('is_premium', True) 
    
    if operation_type in ['script', 'summary', 'tweet'] and not is_user_premium:
        return jsonify({
            'status': 'premium_locked',
            'result': '🔒 Subscription Required! Upgrade to MintNews Premium to unlock this tool.'
        })

    article = NewsArticle.query.get(int(article_id))
    if not article:
        return jsonify({'result': 'Error: Article missing.'})

    if operation_type == 'script':
        prompt = f"Convert this news into a video script layout in {target_lang}. Content: {article.content}"
    elif operation_type == 'summary':
        prompt = f"Generate a clean analytical summary in {target_lang}. Content: {article.content}"
    elif operation_type == 'tweet':
        prompt = f"Create an engaging viral X/Twitter thread layout in {target_lang}. Content: {article.content}"
    else:
        prompt = f"Process for '{operation_type}' in {target_lang}. Content: {article.content}"

    result = query_mistral_production(prompt)
    if "success" in result:
        return jsonify({'status': 'success', 'result': result["text"]})
    else:
        return jsonify({'result': result["error"]})

@ai_bp.route('/jarvis-chat', methods=['POST'])
def jarvis_chat():
    data = request.get_json() or {}
    user_prompt = data.get('prompt', '').strip()
    if not user_prompt:
        return jsonify({'response': 'Prompt empty.'})
    system_instruction = "You are Jarvis, the core system AI of MintNews V4. Help in fluid Hinglish."
    result = query_mistral_production(user_prompt, system_instruction=system_instruction)
    if "success" in result:
        return jsonify({'response': result["text"]})
    return jsonify({'response': result["error"]})
