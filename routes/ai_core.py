from flask import Blueprint, jsonify, request, current_app
from extensions import db, limiter
from models import User, NewsArticle
from flask_jwt_extended import jwt_required, get_jwt_identity
from groq import Groq
import os
import requests
from datetime import datetime

ai_bp = Blueprint('ai_bp', __name__)

def get_groq_client():
    """Initializes and returns the Groq client securely from environment hooks"""
    api_key = os.environ.get('GROQ')
    if not api_key:
        # Fallback tracking if environment variables are unassigned
        api_key = "GROQ_API_KEY_FROM_ENVIRONMENT"
    return Groq(api_key=api_key)

# ==============================================================================
# ROUTE 1: CORE ENGINE FOR GENERATING DISCRETE CONTENT TYPES (WITH PAYWALL)
# ==============================================================================
@ai_bp.route('/process-article', methods=['POST'])
@jwt_required()
@limiter.limit("30 per hour")
def process_article():
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    article_id = data.get('article_id')
    operation_type = data.get('operation') # summary, tweet, detailed, script, blog, audio
    target_lang = data.get('language', 'English')
    
    if not article_id or not operation_type:
        return jsonify({'error': 'Missing required execution matrix attributes'}), 400
        
    user = User.query.get(int(user_id))
    article = NewsArticle.query.get(int(article_id))
    
    if not user or not article:
        return jsonify({'error': 'Target entity resources not found within network'}), 404

    # 🛑 THE STRICT SUBSCRIPTION PAYWALL MANAGEMENT SYSTEM
    premium_operations = ['detailed', 'script', 'blog', 'audio']
    if operation_type in premium_operations and not user.is_premium_active:
        return jsonify({
            'error': 'Premium Access Denied',
            'message': 'This advanced feature requires an active subscription. Watch ads in your wallet node to unlock premium tier!',
            'action_required': 'SUBSCRIPTION_REDIRECTION'
        }), 402

    try:
        client = get_groq_client()
        
        # 🧵 OPERATION 1: TWEET GENERATOR (FREE TIER)
        if operation_type == 'tweet':
            if article.ai_tweet_content:
                return jsonify({'status': 'cached', 'result': article.ai_tweet_content})
                
            prompt = f"Read this article and write a viral technical tweet with hashtags in {target_lang}. Article: {article.content}"
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-70b-8192",
                temperature=0.7
            )
            article.ai_tweet_content = chat_completion.choices[0].message.content
            db.session.commit()
            return jsonify({'status': 'generated', 'result': article.ai_tweet_content})

        # 🧵 OPERATION 2: SHORT FLASH SUMMARY (FREE TIER)
        elif operation_type == 'summary':
            if article.ai_summary_short:
                return jsonify({'status': 'cached', 'result': article.ai_summary_short})
                
            prompt = f"Provide a brief, crisp 3-bullet points bullet summary in {target_lang} for this: {article.content}"
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-70b-8192",
                temperature=0.3
            )
            article.ai_summary_short = chat_completion.choices[0].message.content
            db.session.commit()
            return jsonify({'status': 'generated', 'result': article.ai_summary_short})

        # 🧵 OPERATION 3: DETAILED DEEP BRIEFING (PREMIUM ONLY)
        elif operation_type == 'detailed':
            if article.ai_detailed_brief:
                return jsonify({'status': 'cached', 'result': article.ai_detailed_brief})
                
            prompt = f"Perform a comprehensive financial and macroeconomic analytical deep dive on this news in {target_lang}. Break into market impact, structural analysis, and forecast tables: {article.content}"
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-70b-8192",
                temperature=0.5
            )
            article.ai_detailed_brief = chat_completion.choices[0].message.content
            db.session.commit()
            return jsonify({'status': 'generated', 'result': article.ai_detailed_brief})

        # 🧵 OPERATION 4: VIDEO/YOUTUBE SCRIPT GENERATOR (PREMIUM ONLY)
        elif operation_type == 'script':
            if article.ai_video_script:
                return jsonify({'status': 'cached', 'result': article.ai_video_script})
                
            prompt = f"Convert this news item into an engaging, high-retention multi-minute video script for a content creator. Output must include screen cues, hook, body metrics, and call-to-action in the language {target_lang}. Content: {article.content}"
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-70b-8192",
                temperature=0.8
            )
            article.ai_video_script = chat_completion.choices[0].message.content
            db.session.commit()
            return jsonify({'status': 'generated', 'result': article.ai_video_script})

        # 🧵 OPERATION 5: LONG FORM BLOG EXPANSION (PREMIUM ONLY)
        elif operation_type == 'blog':
            if article.ai_blog_expansion:
                return jsonify({'status': 'cached', 'result': article.ai_blog_expansion})
                
            prompt = f"Write an optimized, structured SEO blog post based on this article. Include an eye-catching title, H2/H3 subheadings, an expert introduction, and an outlook conclusion in {target_lang}. Data source: {article.content}"
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-70b-8192",
                temperature=0.6
            )
            article.ai_blog_expansion = chat_completion.choices[0].message.content
            db.session.commit()
            return jsonify({'status': 'generated', 'result': article.ai_blog_expansion})

        # 🔊 OPERATION 6: ELEVENLABS AUDIO COMPILING PIPELINE (PREMIUM ONLY)
        elif operation_type == 'audio':
            if article.audio_file_path and os.path.exists(article.audio_file_path):
                return jsonify({'status': 'cached', 'audio_url': f"/static/audio/{os.path.basename(article.audio_file_path)}"})

            # Establish safe fallbacks for transcription text
            text_to_speak = article.ai_summary_short if article.ai_summary_short else article.content[:300]
            
            eleven_key = os.environ.get('Elevenlabs', 'sk_33d3fec447ba8b088d7d6d175667074cfd15d6078f7a5c6a')
            voice_id = "21m00Tcm4TlvDq8ikWAM" # High-quality Rachel/Adam baseline variant voice node
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": eleven_key
            }
            payload = {
                "text": text_to_speak,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}
            }
            
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                # Ensure local static media folders exist natively
                audio_dir = os.path.join('static', 'audio')
                os.makedirs(audio_dir, exist_ok=True)
                
                filename = f"news_voice_{article.id}.mp3"
                full_path = os.path.join(audio_dir, filename)
                
                with open(full_path, 'wb') as f:
                    f.write(response.content)
                    
                article.audio_file_path = full_path
                db.session.commit()
                return jsonify({'status': 'compiled', 'audio_url': f"/static/audio/{filename}"})
            else:
                return jsonify({'error': 'ElevenLabs processing node failure', 'details': response.text}), 502

        else:
            return jsonify({'error': 'Invalid algorithmic operational parameter'}), 400

    except Exception as e:
        return jsonify({'error': 'Critical AI core pipeline failure execution error', 'details': str(e)}), 500

# ==============================================================================
# ROUTE 2: THE INTERACTIVE CONVERSATIONAL MULTILINGUAL CHAT SYSTEM (JARVIS NODE)
# ==============================================================================
@ai_bp.route('/jarvis-chat', methods=['POST'])
@jwt_required()
@limiter.limit("50 per hour")
def jarvis_chat():
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    user_prompt = data.get('prompt')
    chat_history = data.get('history', []) # Accept conversational context trees
    
    if not user_prompt:
        return jsonify({'error': 'Input message prompt cannot be empty'}), 400
        
    user = User.query.get(int(user_id))
    if not user:
        return jsonify({'error': 'User tracking profile missing'}), 404

    # Build cognitive system matrix parameters based on tier limits
    tier_status = "PREMIUM ACCOUNT ACTIVE" if user.is_premium_active else "FREE BASIC ACCOUNT LIMITS APPLY"
    system_instruction = (
        f"You are Jarvis, the system intelligence node of MintNews Network V4. "
        f"The user speaking with you has a {tier_status}. "
        f"Be precise, highly analytical regarding tech, forex, and crypto variables. "
        f"Always answer directly in whatever language comfortable to the user (Hindi, English, or mixed Hinglish)."
    )

    try:
        client = get_groq_client()
        messages = [{"role": "system", "content": system_instruction}]
        
        # Inject context logs safely
        for msg in chat_history[-6:]: # Restrict buffer lengths for tokens allocation controls
            messages.append({"role": msg.get("role"), "content": msg.get("content")})
            
        messages.append({"role": "user", "content": user_prompt})
        
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama3-70b-8192",
            temperature=0.7,
            max_tokens=1024
        )
        
        ai_response = chat_completion.choices[0].message.content
        return jsonify({
            'node_status': 'online',
            'response': ai_response,
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        return jsonify({'error': 'Jarvis communication matrix error', 'details': str(e)}), 500
