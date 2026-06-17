from flask import Blueprint, jsonify, request
from extensions import db
from models import NewsArticle
from groq import Groq
import os

ai_bp = Blueprint('ai_bp', __name__)

@ai_bp.route('/process-article', methods=['POST'])
def process_article():
    data = request.get_json() or {}
    article_id = data.get('article_id')
    operation_type = data.get('operation')
    target_lang = data.get('language', 'English')
    
    article = NewsArticle.query.get(int(article_id))
    if not article:
        return jsonify({'result': 'Error: Target article not found in database.'})

    api_key = os.environ.get('GROQ')
    if not api_key:
        return jsonify({'result': 'Error: GROQ API Key missing in Render Environment Settings.'})

    try:
        # 🛑 FIX: Clear Render's internal hidden proxies to prevent client init crashes
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)
        os.environ.pop('http_proxy', None)
        os.environ.pop('https_proxy', None)

        client = Groq(api_key=api_key)
        prompt = f"Perform operation '{operation_type}' on this news content. Respond comprehensively in {target_lang}. Content: {article.content}"
        
        models_pool = ["llama-3.3-70b-versatile", "llama3-70b-8192"]
        ai_response = None
        last_err = ""
        
        for m in models_pool:
            try:
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=m,
                    temperature=0.5
                )
                ai_response = chat_completion.choices[0].message.content
                break
            except Exception as e:
                last_err = str(e)
                continue
                
        if ai_response:
            return jsonify({'status': 'success', 'result': ai_response})
        else:
            return jsonify({'result': f"AI Model Error: {last_err}"})
            
    except Exception as e:
        return jsonify({'result': f"Critical Interface Error: {str(e)}"})

@ai_bp.route('/jarvis-chat', methods=['POST'])
def jarvis_chat():
    data = request.get_json() or {}
    user_prompt = data.get('prompt', '')
    
    if not user_prompt:
        return jsonify({'response': 'Prompt cannot be empty.'})

    api_key = os.environ.get('GROQ')
    if not api_key:
        return jsonify({'response': 'Error: GROQ variable missing on Render settings.'})

    try:
        # 🛑 FIX: Clear proxies for Jarvis console too
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)
        os.environ.pop('http_proxy', None)
        os.environ.pop('https_proxy', None)

        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are Jarvis, the system engine of MintNews V4. Respond directly in fluid conversational Hinglish (mixed Hindi/English)."},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7
        )
        return jsonify({'response': chat_completion.choices[0].message.content})
    except Exception as e:
        return jsonify({'response': f"Jarvis Connection Error: {str(e)}"})
