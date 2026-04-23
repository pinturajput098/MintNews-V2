import os
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3
from datetime import datetime
import google.generativeai as genai

app = Flask(__name__)
app.secret_key = "pintu_ai_secret"

# --- API KEYS ---
GNEWS_KEY = '5b8559e3138b18090304c361c25653b0'
MARKETAUX_KEY = 'YSU6oi4R1R0WahkqNdMWRUMyH5OPQSX8NuQ7nL3Y'

# Gemini Setup (Key Render ke Environment se lega)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# --- DATABASE SETUP ---
def get_db_connection():
    conn = sqlite3.connect('mint_news_v7.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, 
                  image TEXT, category TEXT, date TEXT, author TEXT, views INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS comments 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, news_id TEXT, user TEXT, text TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS subscribers (email TEXT PRIMARY KEY)''')
    conn.commit()
    conn.close()

init_db()

# --- GEMINI AI SUMMARY FUNCTION ---
def get_ai_summary(text):
    try:
        # Gemini Model use kar rahe hain
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"Summarize this news in 3 short bullet points in Hindi. Provide only the bullet points: {text}"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Summary unavailable: {str(e)}"

# --- ROUTES ---
@app.route('/')
def index():
    cat = request.args.get('category', 'india')
    search = request.args.get('search')
    
    conn = get_db_connection()
    local_news = conn.execute("SELECT * FROM news ORDER BY id DESC LIMIT 5").fetchall()
    
    api_articles = []
    try:
        if cat == 'business':
            url = f"https://api.marketaux.com/v1/news/all?symbols=EURUSD,BTC&api_token={MARKETAUX_KEY}"
            res = requests.get(url).json()
            raw = res.get('data', [])
            for a in raw:
                api_articles.append({
                    'title': a.get('title'), 
                    'desc': a.get('description'), 
                    'url': a.get('url'), 
                    'img': a.get('image_url') or 'https://via.placeholder.com/500', 
                    'tag': 'FOREX', 
                    'date': a.get('published_at', '2026-04-23')[:10]
                })
        else:
            q = search if search else (cat if cat != 'india' else 'india news')
            url = f"https://gnews.io/api/v4/search?q={q}&lang=hi&apikey={GNEWS_KEY}"
            res = requests.get(url).json()
            for a in res.get('articles', []):
                api_articles.append({
                    'title': a.get('title'), 
                    'desc': a.get('description'), 
                    'url': a.get('url'), 
                    'img': a.get('image'), 
                    'tag': cat.upper(), 
                    'date': a.get('publishedAt', '2026-04-23')[:10]
                })
    except Exception as e:
        print(f"API Error: {e}")
    
    conn.close()
    featured = api_articles[0] if api_articles else None
    return render_template('index.html', articles=api_articles[1:], featured=featured, local_news=local_news, cat=cat)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        image = request.form.get('image')
        cat = request.form.get('category')
        date = datetime.now().strftime("%Y-%m-%d")
        
        conn = get_db_connection()
        conn.execute("INSERT INTO news (title, content, image, category, date, author) VALUES (?,?,?,?,?,?)",
                     (title, content, image, cat, date, "Piyush Rai"))
        conn.commit()
        conn.close()
        return "<h1>Success! News Posted Successfully!</h1><br><a href='/admin'>Post Another</a> | <a href='/'>Go Home</a>"
    return render_template('admin.html')

@app.route('/api/ai-summarize', methods=['POST'])
def ai_summarize():
    data = request.get_json()
    text = data.get('text', '')
    summary = get_ai_summary(text)
    return jsonify({"summary": summary})

if __name__ == '__main__':
    app.run(debug=True)

