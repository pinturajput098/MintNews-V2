from flask import Blueprint, jsonify, request
from extensions import db
from models import NewsArticle
import requests
import os

ai_bp = Blueprint('ai_bp', __name__)

def query_openrouter_pool(prompt, system_instruction=None):
    """Loops through currently active 100% free models on OpenRouter to guarantee execution"""
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        return {"error": "OPENROUTER_API_KEY missing in Render settings variable matrix."}

    # 🚀 POOL OF LIVE 100% FREE Tier OpenRouter Models
    free_models_pool = [
        "meta-llama/llama-3.1-8b-instruct:free",
        "google/gemma-2-9b-it:free",
        "mistralai/mistral-7b-instruct:free"
    ]
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    last_error_log = ""
    for model_id in free_models_pool:
        try:
            payload = {
                "model": model_id,
                "messages": messages,
                "temperature": 0.6
            }
            response = requests.post(url, headers=headers, json=payload, timeout=12)
            res_data = response.json()
            
            if 'choices' in res_data and len(res_data['choices']) > 0:
                return {"success": True, "text": res_data['choices'][0]['message']['content']}
            elif 'error' in res_data:
                last_error_log = res_data['error'].get('message', str(res_data))
        except Exception as e:
            last_error_log = str(e)
            continue
            
    return {"error": f"All free engines busy. Trace log: {last_error_log}"}

@ai_bp.route('/process-article', methods=['POST'])
def process_article():
    data = request.get_json() or {}
    article_id = data.get('article_id')
    operation_type = data.get('operation')
    target_lang = data.get('language', 'English')
    
    article = NewsArticle.query.get(int(article_id))
    if not article:
        return jsonify({'result': 'Error: Article reference object missing.'})

    prompt = f"Execute operational analysis for '{operation_type}' on this news dataset. Respond comprehensively and strictly in {target_lang}. News Text: {article.content}"
    
    engine_result = query_openrouter_pool(prompt)
    if "success" in engine_result:
        return jsonify({'status': 'success', 'result': engine_result["text"]})
    else:
        return jsonify({'result': f"Engine Error: {engine_result['error']}"})

@ai_bp.route('/jarvis-chat', methods=['POST'])
def jarvis_chat():
    data = request.get_json() or {}
    user_prompt = data.get('prompt', '')
    
    if not user_prompt:
        return jsonify({'response': 'Prompt stream input empty.'})

    system_instruction = "You are Jarvis, the direct operational artificial interface of MintNews V4 system core. Answer smartly and elegantly in natural fluid Hinglish."
    
    engine_result = query_openrouter_pool(user_prompt, system_instruction=system_instruction)
    if "success" in engine_result:
        return jsonify({'response': engine_result["text"]})
    else:
        return jsonify({'response': f"Jarvis Routing Error: {engine_result['error']}"})
