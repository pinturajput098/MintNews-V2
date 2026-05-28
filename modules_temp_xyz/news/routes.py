"""
MintNews Network V3 — News & Content Module
modules/news/routes.py + tasks/news_fetcher.py
Features: Multi-source API, Dedup, Translation, Categories,
          Infinite Scroll, Rich Editor, SEO, TTS, Live Blog
"""

import hashlib
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, List

import feedparser
import requests
from flask import (
    Blueprint, render_template, request, jsonify,
    redirect, url_for, flash, abort, current_app
)
from flask_login import login_required, current_user
from python_slugify import slugify

from app import db, cache, limiter
from models import (
    Article, Category, Tag, Comment, Reaction, Bookmark,
    ArticleViewEvent, User, Notification, SearchQuery, PollVote
)
from modules.auth.routes import role_required, premium_required
from utils.email import send_email

news_bp = Blueprint("news", __name__, template_folder="templates")


# ──────────────────────────────────────────────────────────────
# NEWS FEED — MAIN LISTINGS
# ──────────────────────────────────────────────────────────────
@news_bp.route("/")
@news_bp.route("/feed")
def index():
    page     = request.args.get("page", 1, type=int)
    category = request.args.get("cat")
    lang     = request.args.get("lang", "en")
    q        = request.args.get("q", "").strip()

    query = Article.query.filter_by(status="published")

    if category:
        cat = Category.query.filter_by(slug=category).first_or_404()
        query = query.filter_by(category_id=cat.id)

    if lang != "all":
        query = query.filter_by(language=lang)

    if q:
        query = query.filter(
            (Article.title.ilike(f"%{q}%")) |
            (Article.summary.ilike(f"%{q}%"))
        )
        # Log search
        sq = SearchQuery(
            query=q, user_id=current_user.id if current_user.is_authenticated else None,
            ip_address=request.remote_addr
        )
        db.session.add(sq)
        db.session.commit()

    articles = query.order_by(Article.published_at.desc()).paginate(
        page=page, per_page=current_app.config["NEWS_PER_PAGE"], error_out=False
    )

    # Infinite scroll: return JSON if AJAX
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({
            "articles": [a.to_dict() for a in articles.items],
            "has_next": articles.has_next,
            "next_page": articles.next_num,
        })

    categories  = Category.query.filter_by(is_active=True).order_by(Category.sort_order).all()
    breaking    = Article.query.filter_by(status="published", is_breaking=True).order_by(Article.published_at.desc()).limit(5).all()
    featured    = Article.query.filter_by(status="published", is_featured=True).order_by(Article.published_at.desc()).limit(6).all()
    trending    = cache.get("trending_articles") or _get_trending_articles()

    return render_template(
        "news/feed.html",
        articles=articles, categories=categories,
        breaking=breaking, featured=featured,
        trending=trending, query=q,
    )


@news_bp.route("/<slug>")
def article_detail(slug: str):
    article = Article.query.filter_by(slug=slug).first()

    # Check redirect for old slugs
    if not article:
        article = Article.query.filter(
            Article.old_slugs.contains([slug])
        ).first()
        if article:
            return redirect(url_for("news.article_detail", slug=article.slug), 301)
        abort(404)

    # Track view
    _track_article_view(article)

    # Increment counter
    article.views_count += 1
    db.session.commit()

    # Related articles via category + tags
    related = Article.query.filter(
        Article.category_id == article.category_id,
        Article.id != article.id,
        Article.status == "published",
    ).order_by(Article.published_at.desc()).limit(6).all()

    # Comments (top-level only, nested loaded lazily)
    comments = Comment.query.filter_by(
        article_id=article.id, parent_id=None, is_hidden=False
    ).order_by(Comment.created_at.desc()).limit(25).all()

    # User bookmark / reaction state
    user_bookmarked = False
    user_reaction   = None
    if current_user.is_authenticated:
        bm = Bookmark.query.filter_by(user_id=current_user.id, article_id=article.id).first()
        user_bookmarked = bool(bm)
        rx = Reaction.query.filter_by(user_id=current_user.id, article_id=article.id).first()
        user_reaction = rx.emoji if rx else None

    return render_template(
        "news/article.html",
        article=article, related=related, comments=comments,
        user_bookmarked=user_bookmarked, user_reaction=user_reaction,
    )


def _track_article_view(article: Article):
    view = ArticleViewEvent(
        article_id=article.id,
        user_id=current_user.id if current_user.is_authenticated else None,
        session_id=request.cookies.get("session"),
        ip_address=request.remote_addr,
        referrer=request.referrer,
    )
    db.session.add(view)


def _get_trending_articles() -> List[Article]:
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    articles = Article.query.filter(
        Article.status == "published",
        Article.published_at >= since,
    ).order_by(Article.views_count.desc()).limit(10).all()
    cache.set("trending_articles", articles, timeout=300)
    return articles


# ──────────────────────────────────────────────────────────────
# CATEGORY GRID
# ──────────────────────────────────────────────────────────────
@news_bp.route("/category/<slug>")
def category_feed(slug: str):
    cat = Category.query.filter_by(slug=slug, is_active=True).first_or_404()
    page = request.args.get("page", 1, type=int)
    articles = Article.query.filter_by(
        category_id=cat.id, status="published"
    ).order_by(Article.published_at.desc()).paginate(
        page=page, per_page=current_app.config["NEWS_PER_PAGE"], error_out=False
    )
    return render_template("news/category.html", category=cat, articles=articles)


# ──────────────────────────────────────────────────────────────
# ARTICLE REACTIONS
# ──────────────────────────────────────────────────────────────
@news_bp.route("/<int:article_id>/react", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def react_to_article(article_id: int):
    emoji = request.json.get("emoji")
    VALID_EMOJIS = {"heart", "fire", "rocket", "thinking", "chart"}
    if emoji not in VALID_EMOJIS:
        return jsonify(error="Invalid emoji"), 400

    existing = Reaction.query.filter_by(
        user_id=current_user.id, article_id=article_id
    ).first()

    if existing:
        if existing.emoji == emoji:
            db.session.delete(existing)
        else:
            existing.emoji = emoji
    else:
        r = Reaction(user_id=current_user.id, article_id=article_id, emoji=emoji)
        db.session.add(r)

    db.session.commit()

    counts = {}
    for rx in Reaction.query.filter_by(article_id=article_id).all():
        counts[rx.emoji] = counts.get(rx.emoji, 0) + 1

    return jsonify(success=True, counts=counts)


# ──────────────────────────────────────────────────────────────
# COMMENTS — NESTED THREADED
# ──────────────────────────────────────────────────────────────
@news_bp.route("/<int:article_id>/comments", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def post_comment(article_id: int):
    Article.query.get_or_404(article_id)
    content = request.json.get("content", "").strip()
    parent_id = request.json.get("parent_id")

    if not content or len(content) < 2:
        return jsonify(error="Comment too short"), 400
    if len(content) > 5000:
        return jsonify(error="Comment too long"), 400

    # Spam check
    spam_score = _check_spam(content)
    if spam_score > 0.9:
        return jsonify(error="Comment flagged as spam"), 400

    # Render markdown
    import bleach, markdown as md
    html = bleach.clean(md.markdown(content), tags=bleach.sanitizer.ALLOWED_TAGS + ["p", "br", "h1", "h2", "h3"])

    comment = Comment(
        article_id=article_id,
        author_id=current_user.id,
        parent_id=parent_id,
        content=content,
        content_html=html,
        spam_score=spam_score,
    )
    db.session.add(comment)

    # Award XP
    current_user.add_xp(5)
    current_user.mintcoins += current_app.config["MINTCOIN_COMMENT_POST"]
    db.session.commit()

    # Notify parent commenter
    if parent_id:
        parent_comment = Comment.query.get(parent_id)
        if parent_comment and parent_comment.author_id != current_user.id:
            notif = Notification(
                user_id=parent_comment.author_id,
                type="comment_reply",
                title=f"{current_user.display_name} replied to your comment",
                message=content[:200],
                link=url_for("news.article_detail", slug=comment.article.slug, _anchor=f"comment-{comment.id}"),
            )
            db.session.add(notif)
            db.session.commit()

    return jsonify(
        success=True,
        comment={
            "id": comment.id,
            "content_html": comment.content_html,
            "author": current_user.display_name,
            "avatar": current_user.avatar_url or "",
            "created_at": comment.created_at.isoformat(),
        }
    )


@news_bp.route("/comments/<int:comment_id>/vote", methods=["POST"])
@login_required
def vote_comment(comment_id: int):
    direction = request.json.get("direction")  # "up" or "down"
    comment = Comment.query.get_or_404(comment_id)
    if direction == "up":
        comment.upvotes += 1
    elif direction == "down":
        comment.downvotes += 1
    db.session.commit()
    return jsonify(upvotes=comment.upvotes, downvotes=comment.downvotes)


def _check_spam(text: str) -> float:
    """Simple heuristic spam scorer 0-1."""
    spam_patterns = [
        r"http[s]?://\S+",   # Multiple URLs
        r"\$\$\$", r"click here", r"buy now", r"free money",
        r"(.)\1{4,}",          # Repeated characters
    ]
    score = 0.0
    for p in spam_patterns:
        if re.search(p, text, re.IGNORECASE):
            score += 0.25
    return min(score, 1.0)


# ──────────────────────────────────────────────────────────────
# BOOKMARKS
# ──────────────────────────────────────────────────────────────
@news_bp.route("/<int:article_id>/bookmark", methods=["POST"])
@login_required
def toggle_bookmark(article_id: int):
    Article.query.get_or_404(article_id)
    folder = request.json.get("folder", "General")

    existing = Bookmark.query.filter_by(
        user_id=current_user.id, article_id=article_id
    ).first()

    if existing:
        db.session.delete(existing)
        saved = False
    else:
        bm = Bookmark(user_id=current_user.id, article_id=article_id, folder=folder)
        db.session.add(bm)
        saved = True
        current_user.add_xp(1)

    db.session.commit()
    return jsonify(saved=saved)


@news_bp.route("/bookmarks")
@login_required
def bookmarks():
    folders = db.session.query(Bookmark.folder).filter_by(
        user_id=current_user.id
    ).distinct().all()
    folder_name = request.args.get("folder", "General")
    bms = Bookmark.query.filter_by(
        user_id=current_user.id, folder=folder_name
    ).order_by(Bookmark.created_at.desc()).all()
    return render_template("news/bookmarks.html", bookmarks=bms, folders=[f[0] for f in folders], current_folder=folder_name)


# ──────────────────────────────────────────────────────────────
# LIVE BLOG
# ──────────────────────────────────────────────────────────────
@news_bp.route("/live/<slug>")
def live_blog(slug: str):
    article = Article.query.filter_by(slug=slug, status="published").first_or_404()
    updates = Comment.query.filter_by(
        article_id=article.id, is_hidden=False
    ).order_by(Comment.created_at.desc()).limit(50).all()
    return render_template("news/live_blog.html", article=article, updates=updates)


@news_bp.route("/live/<int:article_id>/updates")
def live_blog_updates(article_id: int):
    """SSE endpoint for live blog auto-refresh."""
    since = request.args.get("since")
    query = Comment.query.filter_by(article_id=article_id, is_hidden=False)
    if since:
        try:
            dt = datetime.fromisoformat(since)
            query = query.filter(Comment.created_at > dt)
        except ValueError:
            pass
    updates = query.order_by(Comment.created_at.asc()).limit(20).all()
    return jsonify({
        "updates": [
            {
                "id": c.id, "content_html": c.content_html,
                "author": c.author.display_name,
                "created_at": c.created_at.isoformat()
            } for c in updates
        ]
    })


# ──────────────────────────────────────────────────────────────
# AUDIO ARTICLE (TTS)
# ──────────────────────────────────────────────────────────────
@news_bp.route("/<int:article_id>/generate-audio", methods=["POST"])
@login_required
@limiter.limit("5 per hour")
def generate_audio(article_id: int):
    article = Article.query.get_or_404(article_id)
    if article.audio_url:
        return jsonify(audio_url=article.audio_url)

    from tasks.tts import generate_article_audio
    generate_article_audio.delay(article_id)
    return jsonify(message="Audio generation queued. Refresh in a minute.")


# ──────────────────────────────────────────────────────────────
# SEARCH
# ──────────────────────────────────────────────────────────────
@news_bp.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return render_template("news/search.html", articles=[], query="")

    page = request.args.get("page", 1, type=int)
    articles = Article.query.filter(
        Article.status == "published",
        (Article.title.ilike(f"%{q}%")) |
        (Article.summary.ilike(f"%{q}%")) |
        (Article.content.ilike(f"%{q}%"))
    ).order_by(Article.published_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    sq = SearchQuery(
        query=q, result_count=articles.total,
        user_id=current_user.id if current_user.is_authenticated else None,
        ip_address=request.remote_addr,
    )
    db.session.add(sq)
    db.session.commit()

    return render_template("news/search.html", articles=articles, query=q)


# ──────────────────────────────────────────────────────────────
# TRANSLATION API
# ──────────────────────────────────────────────────────────────
@news_bp.route("/<int:article_id>/translate/<lang>")
@limiter.limit("30 per hour")
def translate_article(article_id: int, lang: str):
    article = Article.query.get_or_404(article_id)
    SUPPORTED = {"hi", "es", "fr", "de", "ar", "pt", "bn"}
    if lang not in SUPPORTED:
        return jsonify(error="Unsupported language"), 400

    if article.translations and lang in article.translations:
        return jsonify(translation=article.translations[lang])

    from tasks.translate import translate_article_task
    translate_article_task.delay(article_id, lang)
    return jsonify(message="Translation in progress. Try again shortly.")


# ──────────────────────────────────────────────────────────────
# ADMIN — EDITOR ROUTES
# ──────────────────────────────────────────────────────────────
@news_bp.route("/editor/new", methods=["GET", "POST"])
@login_required
@role_required("editor", "admin")
def editor_new():
    if request.method == "POST":
        return _save_article(None)
    categories = Category.query.filter_by(is_active=True).all()
    return render_template("news/editor.html", article=None, categories=categories)


@news_bp.route("/editor/<int:article_id>", methods=["GET", "POST"])
@login_required
@role_required("editor", "admin")
def editor_edit(article_id: int):
    article = Article.query.get_or_404(article_id)
    if request.method == "POST":
        return _save_article(article)
    categories = Category.query.filter_by(is_active=True).all()
    return render_template("news/editor.html", article=article, categories=categories)


def _save_article(article: Optional[Article]):
    data = request.json or request.form
    import bleach, markdown as md

    title    = data.get("title", "").strip()
    content  = data.get("content", "").strip()
    cat_id   = data.get("category_id", type=int)
    status   = data.get("status", "draft")
    is_new   = article is None

    if not title:
        return jsonify(error="Title is required"), 400

    if is_new:
        article = Article(
            author_id=current_user.id,
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
        )
        db.session.add(article)
    else:
        # Save version before overwriting
        from models import ArticleVersion
        version = ArticleVersion(
            article_id=article.id,
            version_num=len(article.versions) + 1,
            title=article.title,
            content=article.content,
            edited_by=current_user.id,
            change_note=data.get("change_note", ""),
        )
        db.session.add(version)
        # Track old slug
        if article.slug and title != article.title:
            old_slugs = article.old_slugs or []
            old_slugs.append(article.slug)
            article.old_slugs = old_slugs

    article.title       = title
    article.content     = content
    article.content_html= bleach.clean(md.markdown(content), tags=bleach.sanitizer.ALLOWED_TAGS + ["p", "h1", "h2", "h3", "br", "blockquote", "code", "pre"])
    article.category_id = cat_id
    article.status      = status
    article.language    = data.get("language", "en")
    article.is_featured = bool(data.get("is_featured"))
    article.is_breaking = bool(data.get("is_breaking"))
    article.is_sponsored= bool(data.get("is_sponsored"))

    # Auto-generate slug
    base_slug = slugify(title)
    slug = base_slug
    counter = 1
    while Article.query.filter(Article.slug == slug, Article.id != (article.id or 0)).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    article.slug = slug

    # Auto-compute read time (avg 200 wpm)
    word_count = len(re.findall(r"\w+", content))
    article.read_time_minutes = max(1, word_count // 200)

    # Auto-generate SEO
    article.meta_title       = title[:70]
    article.meta_description = (article.summary or content[:150]).replace("\n", " ")[:160]

    if status == "published" and not article.published_at:
        scheduled = data.get("scheduled_at")
        if scheduled:
            article.scheduled_at = datetime.fromisoformat(scheduled)
        else:
            article.published_at = datetime.now(timezone.utc)

    db.session.commit()

    # Queue AI enrichment
    if status == "published":
        from tasks.ai_enrichment import enrich_article
        enrich_article.delay(article.id)

        # Cross-post if configured
        from tasks.social_crosspost import crosspost_article
        crosspost_article.delay(article.id)

    return jsonify(success=True, article_id=article.id, slug=article.slug)


# ──────────────────────────────────────────────────────────────
# BACKGROUND TASK: NEWS FETCHER (used by Celery)
# ──────────────────────────────────────────────────────────────
class NewsFetcher:
    """
    Multi-source asynchronous news aggregation pipeline.
    Sources: GNews API, Marketaux, RSS feeds
    Includes: Deduplication, category routing, AI enrichment trigger
    """

    GNEWS_CATEGORIES = ["general", "world", "business", "technology", "entertainment", "sports", "science", "health"]
    RSS_FEEDS = {
        "forex":  ["https://www.forexfactory.com/ff_calendar.php", "https://www.babypips.com/learn/forex/rss"],
        "crypto": ["https://cointelegraph.com/rss", "https://decrypt.co/feed", "https://bitcoinmagazine.com/.rss/full/"],
        "india":  ["https://www.thehindu.com/news/national/feeder/default.rss", "https://feeds.feedburner.com/ndtvnews-top-stories"],
        "tech":   ["https://techcrunch.com/feed/",
