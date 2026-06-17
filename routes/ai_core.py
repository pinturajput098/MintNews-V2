from flask import Blueprint, jsonify, request
from extensions import db
from models import NewsArticle
import requests
import os

ai_bp = Blueprint('ai_bp', __name__)

def query_huggingface_engine(messages, temperature=0.7):
    """Queries Hugging Face Serverless Inference API using pure stable OpenAI compatible layouts"""
    api_key = os.environ.get('HF_API_KEY')
    if not api_key:
        return {"error": "HF_API_KEY is missing in Render environment variables settings."}

    # Using ultra-stable high-performance free model node
    url = "https://api-inference.huggingface.co/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "messages": messages,
        "max_tokens": 600,
        "temperature": temperature
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        res_data = response.json()
        
        if 'choices' in res_data and len(res_data['choices']) > 0:
            return {"success": True, "text": res_data['choices'][0]['message']['content']}
        elif 'error' in res_data:
            return {"error": res_data['error']}
        else:
            return {"error": f"API structural variance logged: {str(res_data)}"}
    except Exception as e:
        return {"error": str(e)}

@ai_bp.route('/process-article', methods=['POST'])
def process_article():
    data = request.get_json() or {}
    article_id = data.get('article_id')
    operation_type = data.get('operation')
    target_lang = data.get('language', 'English')
    
    article = NewsArticle.query.get(int(article_id))
    if not article:
        return jsonify({'result': 'Error: Target article data sequence missing.'})

    prompt = f"Perform operation '{operation_type}' on this news article text. Respond extensively in fluid {target_lang}. News Content: {article.content}"
    messages = [{"role": "user", "content": prompt}]
    
    result = query_huggingface_engine(messages, temperature=0.5)
    if "success" in result:
        return jsonify({'status': 'success', 'result': result["text"]})
    else:
        return jsonify({'result': f"HuggingFace Engine Error: {result['error']}"})

@ai_bp.route('/jarvis-chat', methods=['POST'])
def jarvis_chat():
    data = request.get_json() or {}
    user_prompt = data.get('prompt', '')
    
    if not user_prompt:
        return jsonify({'response': 'Prompt content stream unassigned.'})

    messages = [
        {"role": "system", "content": "You are Jarvis, the system core AI intelligence node of MintNews V4. Help the user natively in conversational smooth Hinglish."},
        {"role": "user", "content": user_prompt}
    ]
    
    result = query_huggingface_engine(messages, temperature=0.7)
    if "success" in result:
        return jsonify({'response': result["text"]})
    else:
        return jsonify({'response': f"Jarvis Routing Error: {result['error']}"})
