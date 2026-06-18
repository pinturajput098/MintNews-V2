from flask import Blueprint, jsonify, request
from extensions import db
from models import NewsArticle
import requests

ai_bp = Blueprint('ai_bp', __name__)

def query_duckduckgo_free_ai(prompt, system_instruction=None):
    """Queries DuckDuckGo's official free chat endpoint - 100% Free, Zero Keys, Zero Signup"""
    session = requests.Session()
    no_proxies = {"http": None, "https": None}
    
    # Step 1: Fetch the mandatory token/vreq from DuckDuckGo headers
    init_url = "https://duckduckgo.com/duckchat/v1/status"
    headers = {"x-vqd-accept": "1", "User-Agent": "Mozilla/5.0"}
    
    try:
        init_res = session.get(init_url, headers=headers, proxies=no_proxies, timeout=8)
        vqd_token = init_res.headers.get("x-vqd-4")
        if not vqd_token:
            return {"error": "Failed to handshake with Free Chat Stream API"}
            
        # Step 2: Send the prompt to Llama-3-8b via DuckChat protocol
        chat_url = "https://duckduckgo.com/duckchat/v1/chat"
        chat_headers = {
            "x-vqd-4": vqd_token,
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "User-Agent": "Mozilla/5.0"
        }
        
        full_text = prompt
        if system_instruction:
            full_text = f"System Instruction: {system_instruction}\n\nUser Input: {prompt}"
            
        payload = {
            "model": "meta-llama/Llama-3-8b-instruct",
            "messages": [{"role": "user", "content": full_text}]
        }
        
        response = session.post(chat_url, headers=chat_headers, json=payload, proxies=no_proxies, timeout=12)
        
        # Parse the standard Server-Sent Events (SSE) data stream manually
        lines = response.text.split("\n")
        reply_parts = []
        for line in lines:
            if line.startswith("data:"):
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                import json
                try:
                    chunk = json.loads(data_str)
                    if "message" in chunk:
                        reply_parts.append(chunk["message"])
                except:
                    continue
                    
        final_text = "".join(reply_parts)
        if final_text:
            return {"success": True, "text": final_text}
        else:
            return {"error": "Free engine returned empty stream layout."}
            
    except Exception as e:
        return {"error": f"Free Network Interface Failure: {str(e)}"}

@ai_bp.route('/process-article', methods=['POST'])
def process_article():
    data = request.get_json() or {}
    article_id = data.get('article_id')
    operation_type = data.get('operation')
    target_lang = data.get('language', 'English')
    
    article = NewsArticle.query.get(int(article_id))
    if not article:
        return jsonify({'result': 'Error: Target news element not found.'})

    prompt = f"Perform operation '{operation_type}' on this news text. Respond comprehensively in {target_lang}. Content: {article.content}"
    
    result = query_duckduckgo_free_ai(prompt)
    if "success" in result:
        return jsonify({'status': 'success', 'result': result["text"]})
    else:
        return jsonify({'result': f"Engine Error: {result['error']}"})

@ai_bp.route('/jarvis-chat', methods=['POST'])
def jarvis_chat():
    data = request.get_json() or {}
    user_prompt = data.get('prompt', '').strip()
    
    if not user_prompt:
        return jsonify({'response': 'Prompt stream cannot be empty.'})

    system_instruction = "You are Jarvis, the core system engine of MintNews V4. Respond instantly and smartly in conversational Hinglish."
    
    result = query_duckduckgo_free_ai(user_prompt, system_instruction=system_instruction)
    if "success" in result:
        return jsonify({'response': result["text"]})
    else:
        return jsonify({'response': f"Jarvis Connection Error: {result['error']}"})
