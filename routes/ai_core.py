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

@ai_bp.route('/category/<cat_name>', methods=['GET'])
def get_category_news(cat_name):
    clean_cat = cat_name.strip().lower()
    
    # 🚫 BLOCKED CATEGORIES: Strict drop for crypto, forex, tech
    if clean_cat in ['crypto', 'forex', 'tech']:
        return jsonify({'message': 'Category deactivated or restricted'}), 403
        
    articles = NewsArticle.query.filter(NewsArticle.category.ilike(f"%{clean_cat}%")).order_by(NewsArticle.id.desc()).limit(15).all()
    if not articles:
        articles = NewsArticle.query.order_by(NewsArticle.id.desc()).limit(10).all()
    return render_template('category.html', articles=articles, active_category=cat_name)

@ai_bp.route('/process-premium-action', methods=['POST'])
def process_premium_action():
    data = request.get_json() or {}
    article_id = data.get('article_id')
    operation_type = data.get('operation') # 'script', 'summary', 'tweet'
    target_lang = data.get('language', 'Hinglish')
    
    # 🔒 EXCLUSIVE ENFORCEMENT: Enforcing strict simulation check
    is_user_premium = data.get('is_premium', False) 
    
    if operation_type in ['script', 'summary', 'tweet'] and not is_user_premium:
        return jsonify({
            'status': 'premium_locked',
            'result': '🔒 Subscription Required! Script, Summary, and Tweet tools are exclusive to MintNews Premium Members.'
        })

    article = NewsArticle.query.get(int(article_id))
    if not article:
        return jsonify({'result': 'Error: Article missing.'})

    if operation_type == 'script':
        prompt = f"Convert this news into a video script layout with visual cues in {target_lang}. Content: {article.content}"
    elif operation_type == 'summary':
        prompt = f"Generate a clean analytical summary with pointers in {target_lang}. Content: {article.content}"
    elif operation_type == 'tweet':
        prompt = f"Create an engaging X/Twitter thread format in {target_lang}. Content: {article.content}"
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
