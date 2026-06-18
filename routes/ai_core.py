from flask import Blueprint, jsonify, request
from extensions import db
from models import NewsArticle
import requests
import os

ai_bp = Blueprint('ai_bp', __name__)

def query_together_ai(prompt, system_instruction=None):
    """Queries Together AI endpoint using ultra-fast Llama-3-8b infrastructure"""
    api_key = os.environ.get('TOGETHER_API_KEY')
    if not api_key:
        return {"error": "TOGETHER_API_KEY is missing in Render settings."}

    no_proxies = {"http": None, "https": None}
    url = "https://api.together.xyz/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "meta-llama/Llama-3-8b-instruct",
        "messages": messages,
        "max_tokens": 600,
        "temperature": 0.7
    }

    try:
        response = requests.post(url, headers=headers, json=payload, proxies=no_proxies, timeout=10)
        res_data = response.json()
        
        if 'choices' in res_data and len(res_data['choices']) > 0:
            return {"success": True, "text": res_data['choices'][0]['message']['content']}
        else:
            return {"error": f"TogetherAI Error: {str(res_data)}"}
    except Exception as e:
        return {"error": f"Connection Timeout: {str(e)}"}

@ai_bp.route('/process-article', methods=['POST'])
def process_article():
    data = request.get_json() or {}
    article_id = data.get('article_id')
    operation_type = data.get('operation')
    target_lang = data.get('language', 'English')
    
    article = NewsArticle.query.get(int(article_id))
    if not article:
        return jsonify({'result': 'Error: News article reference target missing.'})

    prompt = f"Perform operation '{operation_type}' on this news article text. Respond extensively in fluid {target_lang}. Content: {article.content}"
    
    result = query_together_ai(prompt)
    if "success" in result:
        return jsonify({'status': 'success', 'result': result["text"]})
    else:
        return jsonify({'result': result["error"]})

@ai_bp.route('/jarvis-chat', methods=['POST'])
def jarvis_chat():
    data = request.get_json() or {}
    user_prompt = data.get('prompt', '').strip()
    
    if not user_prompt:
        return jsonify({'response': 'Prompt query cannot be empty.'})

    system_instruction = "You are Jarvis, the core system AI engine of MintNews V4. Respond instantly, smartly, and conversationally in fluid Hinglish (mixed Hindi/English)."
    
    result = query_together_ai(user_prompt, system_instruction=system_instruction)
    if "success" in result:
        return jsonify({'response': result["text"]})
    else:
        return jsonify({'response': f"Jarvis Error: {result['error']}"})
