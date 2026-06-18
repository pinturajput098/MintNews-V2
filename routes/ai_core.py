from flask import Blueprint, jsonify, request
from extensions import db
from models import NewsArticle
import requests
import os

ai_bp = Blueprint('ai_bp', __name__)

def query_mistral_free(prompt, system_instruction=None):
    """Queries Mistral AI La Plateforme official high-speed free tier"""
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

    # Using the absolute fast and stable free model on La Plateforme
    payload = {
        "model": "mistral-small-latest",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 600
    }

    try:
        response = requests.post(url, headers=headers, json=payload, proxies=no_proxies, timeout=12)
        res_data = response.json()
        
        if 'choices' in res_data and len(res_data['choices']) > 0:
            return {"success": True, "text": res_data['choices'][0]['message']['content']}
        elif 'error' in res_data:
            return {"error": res_data['error'].get('message', str(res_data))}
        else:
            return {"error": f"Structural mismatch: {str(res_data)}"}
    except Exception as e:
        return {"error": f"Mistral Network Timeout: {str(e)}"}

@ai_bp.route('/process-article', methods=['POST'])
def process_article():
    data = request.get_json() or {}
    article_id = data.get('article_id')
    operation_type = data.get('operation')
    target_lang = data.get('language', 'English')
    
    article = NewsArticle.query.get(int(article_id))
    if not article:
        return jsonify({'result': 'Error: News node missing.'})

    prompt = f"Perform operation '{operation_type}' on this news article text. Respond extensively in fluid {target_lang}. Content: {article.content}"
    
    result = query_mistral_free(prompt)
    if "success" in result:
        return jsonify({'status': 'success', 'result': result["text"]})
    else:
        return jsonify({'result': f"Mistral Error: {result['error']}"})

@ai_bp.route('/jarvis-chat', methods=['POST'])
def jarvis_chat():
    data = request.get_json() or {}
    user_prompt = data.get('prompt', '').strip()
    
    if not user_prompt:
        return jsonify({'response': 'Prompt query cannot be empty.'})

    system_instruction = "You are Jarvis, the core system AI engine of MintNews V4. Respond instantly, smartly, and conversationally in fluid Hinglish."
    
    result = query_mistral_free(user_prompt, system_instruction=system_instruction)
    if "success" in result:
        return jsonify({'response': result["text"]})
    else:
        return jsonify({'response': f"Jarvis Error: {result['error']}"})
