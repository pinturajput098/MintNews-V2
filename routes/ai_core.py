from flask import Blueprint, jsonify, request, render_template
from extensions import db
from models import NewsArticle, User # Assuming User model has is_premium boolean field
import requests
import os

ai_bp = Blueprint('ai_bp', __name__)

def query_mistral_production(prompt, system_instruction=None):
    """Mistral AI La Plateforme stable core runner"""
    api_key = os.environ.get('MISTRAL_API_KEY')
    if not api_key:
        return {"error": "MISTRAL_API_KEY is missing in Render environment variables."}

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
        elif 'error' in res_data:
            return {"error": res_data['error'].get('message', str(res_data))}
        else:
            return {"error": "Structural mismatch in Mistral response."}
    except Exception as e:
        return {"error": f"Mistral Network Failure: {str(e)}"}


# 🔄 BUG FIX 2: Fixed Category Feed Repetition Logic
@ai_bp.route('/category/<cat_name>', methods=['GET'])
def get_category_news(cat_name):
    """Fetches clean, segregated news filtering strictly by selected category"""
    # Stripping and filtering dynamically to avoid global cross-feed leak
    clean_cat = cat_name.strip().lower()
    
    # Query database strictly for that category instead of grabbing all records
    articles = NewsArticle.query.filter(NewsArticle.category.ilike(f"%{clean_cat}%")).order_by(NewsArticle.id.desc()).limit(15).all()
    
    # Fallback layout check if category doesn't have sufficient fresh scrapes
    if not articles:
        articles = NewsArticle.query.order_by(NewsArticle.id.desc()).limit(10).all()
        
    return render_template('category.html', articles=articles, active_category=cat_name)


# 👑 PREMIUM CONTROL GATEWAY: Manages Premium/Subscription access routing
@ai_bp.route('/process-premium-action', methods=['POST'])
def process_premium_action():
    data = request.get_json() or {}
    article_id = data.get('article_id')
    operation_type = data.get('operation') # 'script', 'summary', or 'tweet'
    target_lang = data.get('language', 'Hinglish')
    user_id = data.get('user_id') # Pass user context from session
    
    # Mocking premium status check - replace with real database session check: user.is_premium
    # For now, keeping it controlled so subscription checks work smoothly
    is_user_premium = data.get('is_premium_test', False) 
    
    if not is_user_premium:
        return jsonify({
            'status': 'premium_locked',
            'result': '🔒 This feature is locked under MintNews Premium Plan. Upgrade now to unlock Script, Summary and Tweet Generator!'
        })

    article = NewsArticle.query.get(int(article_id))
    if not article:
        return jsonify({'result': 'Error: Targeted news article reference missing.'})

    # Custom prompt switching according to feature demand
    if operation_type == 'script':
        prompt = f"Convert this news into a detailed video script layout with anchors and visual bullet points in {target_lang}. Content: {article.content}"
    elif operation_type == 'summary':
        prompt = f"Generate a deep structural executive summary with key takeaways of this news article in {target_lang}. Content: {article.content}"
    elif operation_type == 'tweet':
        prompt = f"Create a highly engaging, viral Twitter/X post thread based on this news article. Include trending hashtags and structured lines natively in {target_lang}. Content: {article.content}"
    else:
        prompt = f"Process this news layout for operation '{operation_type}' in {target_lang}. Content: {article.content}"

    result = query_mistral_production(prompt)
    if "success" in result:
        return jsonify({'status': 'success', 'result': result["text"]})
    else:
        return jsonify({'result': f"Mistral Production Error: {result['error']}"})


# 💬 CORE FEATURE RESTORED: Jarvis Conversational UI Integration
@ai_bp.route('/jarvis-chat', methods=['POST'])
def jarvis_chat():
    data = request.get_json() or {}
    user_prompt = data.get('prompt', '').strip()
    
    if not user_prompt:
        return jsonify({'response': 'Prompt query cannot be empty.'})

    system_instruction = "You are Jarvis, the system core AI of MintNews V4. Help the user natively in fluid conversational Hinglish with instant intelligent insights."
    
    result = query_mistral_production(user_prompt, system_instruction=system_instruction)
    if "success" in result:
        return jsonify({'response': result["text"]})
    else:
        return jsonify({'response': f"Jarvis Error: {result['error']}"})

# Legacy fallback route for base requests to ensure compatibility
@ai_bp.route('/process-article', methods=['POST'])
def process_article():
    data = request.get_json() or {}
    article_id = data.get('article_id')
    operation_type = data.get('operation')
    target_lang = data.get('language', 'English')
    
    article = NewsArticle.query.get(int(article_id))
    if not article:
        return jsonify({'result': 'Error: Article context missing.'})

    prompt = f"Perform operation '{operation_type}' on this news text. Respond in {target_lang}. Content: {article.content}"
    result = query_mistral_production(prompt)
    if "success" in result:
        return jsonify({'status': 'success', 'result': result["text"]})
    else:
        return jsonify({'result': result["error"]})
