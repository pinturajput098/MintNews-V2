"""
MintNews Network V3 — Trading Intelligence Module
modules/trading/routes.py
Features: WebSocket prices, TradingView, Technical Analysis, Economic Calendar,
          Trading Journal, Price Alerts, Backtesting, Position Sizing,
          Sentiment, Correlation Matrix, Fear & Greed, Gas Tracker, etc.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests
from flask import (
    Blueprint, render_template, request, jsonify,
    redirect, url_for, flash, current_app
)
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, leave_room

from app import db, cache, limiter, socketio
from models import (
    TradingJournal, PriceAlert, WatchlistItem, PaperTrade,
    TradingCompetition, MintCoinTransaction, Notification
)
from modules.auth.routes import premium_required

trading_bp = Blueprint("trading", __name__, template_folder="templates")


# ──────────────────────────────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────────────────────────────
@trading_bp.route("/")
@login_required
def dashboard():
    watchlist = WatchlistItem.query.filter_by(user_id=current_user.id).order_by(WatchlistItem.sort_order).all()
    alerts    = PriceAlert.query.filter_by(user_id=current_user.id, is_triggered=False).all()
    recent_trades = TradingJournal.query.filter_by(user_id=current_user.id).order_by(TradingJournal.opened_at.desc()).limit(5).all()
    pnl_summary   = _get_pnl_summary(current_user.id)
    competitions  = TradingCompetition.query.filter_by(is_active=True).order_by(TradingCompetition.start_time.desc()).all()

    return render_template(
        "trading/dashboard.html",
        watchlist=watchlist,
        alerts=alerts,
        recent_trades=recent_trades,
        pnl_summary=pnl_summary,
        symbols=current_app.config["DEFAULT_SYMBOLS"],
        competitions=competitions,
    )


# ──────────────────────────────────────────────────────────────
# LIVE PRICES API (proxied to avoid CORS and protect API keys)
# ──────────────────────────────────────────────────────────────
@trading_bp.route("/api/prices")
@cache.cached(timeout=15, key_prefix=lambda: f"prices_{request.args.get('symbols','BTC,ETH,EUR')}")
def get_live_prices():
    """Fetch live crypto + forex prices via CCXT / Alpha Vantage."""
    symbols = request.args.get("symbols", "BTC/USDT,ETH/USDT").split(",")
    prices  = {}

    # Crypto via Binance (CCXT abstraction)
    try:
        import ccxt
        binance = ccxt.binance()
        for sym in symbols:
            sym = sym.strip()
            if "/" in sym:
                try:
                    ticker = binance.fetch_ticker(sym)
                    prices[sym] = {
                        "price":     ticker["last"],
                        "change_24h": round(ticker.get("percentage", 0), 2),
                        "high_24h":  ticker.get("high"),
                        "low_24h":   ticker.get("low"),
                        "volume":    ticker.get("baseVolume"),
                        "bid":       ticker.get("bid"),
                        "ask":       ticker.get("ask"),
                    }
                except Exception:
                    pass
    except Exception as e:
        current_app.logger.error(f"CCXT error: {e}")

    # Forex via Alpha Vantage
    forex_pairs = [s.strip() for s in symbols if "/" not in s or "USD" in s.upper() and "BTC" not in s.upper()]
    av_key = current_app.config["ALPHA_VANTAGE_KEY"]
    for pair in forex_pairs:
        if len(pair) == 6:  # e.g. EURUSD
            try:
                r = requests.get(
                    "https://www.alphavantage.co/query",
                    params={"function": "CURRENCY_EXCHANGE_RATE",
                            "from_currency": pair[:3], "to_currency": pair[3:],
                            "apikey": av_key},
                    timeout=5
                )
                data = r.json().get("Realtime Currency Exchange Rate", {})
                if data:
                    prices[pair] = {
                        "price": float(data.get("5. Exchange Rate", 0)),
                        "bid": float(data.get("8. Bid Price", 0)),
                        "ask": float(data.get("9. Ask Price", 0)),
                    }
            except Exception as e:
                current_app.logger.error(f"Alpha Vantage error {pair}: {e}")

    return jsonify(prices=prices, timestamp=datetime.now(timezone.utc).isoformat())


# ──────────────────────────────────────────────────────────────
# FEAR & GREED INDEX
# ──────────────────────────────────────────────────────────────
@trading_bp.route("/api/fear-greed")
@cache.cached(timeout=3600, key_prefix="fear_greed")
def fear_greed():
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=30", timeout=5)
        data = r.json()
        return jsonify(data)
    except Exception:
        return jsonify(error="Unable to fetch Fear & Greed index"), 503


# ──────────────────────────────────────────────────────────────
# ECONOMIC CALENDAR
# ──────────────────────────────────────────────────────────────
@trading_bp.route("/api/economic-calendar")
@cache.cached(timeout=3600, key_prefix="economic_calendar")
def economic_calendar():
    """Fetch high-impact economic events via RapidAPI."""
    try:
        r = requests.get(
            "https://economic-calendar1.p.rapidapi.com/economic_calendar",
            headers={
                "X-RapidAPI-Key": current_app.config["RAPIDAPI_KEY"],
                "X-RapidAPI-Host": "economic-calendar1.p.rapidapi.com",
            },
            timeout=10
        )
        events = r.json()
        # Filter high-impact
        high_impact = [e for e in (events if isinstance(events, list) else [])
                       if e.get("impact") in ("High", "3", 3)]
        return jsonify(events=high_impact)
    except Exception as e:
        return jsonify(error=str(e), events=[])


# ──────────────────────────────────────────────────────────────
# GAS TRACKER
# ──────────────────────────────────────────────────────────────
@trading_bp.route("/api/gas")
@cache.cached(timeout=60, key_prefix="gas_tracker")
def gas_tracker():
    prices = {}
    # Ethereum via EtherScan
    try:
        r = requests.get(
            "https://api.etherscan.io/api",
            params={"module": "gastracker", "action": "gasoracle", "apikey": "YourEtherScanKey"},
            timeout=5
        )
        eth = r.json().get("result", {})
        prices["ETH"] = {
            "slow": eth.get("SafeGasPrice"),
            "standard": eth.get("ProposeGasPrice"),
            "fast": eth.get("FastGasPrice"),
        }
    except Exception:
        pass

    return jsonify(gas=prices, timestamp=datetime.now(timezone.utc).isoformat())


# ──────────────────────────────────────────────────────────────
# MARKET CAP TRACKER
# ──────────────────────────────────────────────────────────────
@trading_bp.route("/api/market-cap")
@cache.cached(timeout=300, key_prefix="market_cap")
def market_cap():
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={
                "vs_currency": "usd", "order": "market_cap_desc",
                "per_page": 100, "page": 1, "sparkline": False
            },
            timeout=10
        )
        coins = r.json()
        return jsonify(coins=coins)
    except Exception as e:
        return jsonify(error=str(e)), 503


# ──────────────────────────────────────────────────────────────
# CURRENCY CONVERTER
# ──────────────────────────────────────────────────────────────
@trading_bp.route("/api/convert")
def currency_convert():
    from_cur = request.args.get("from", "USD")
    to_cur   = request.args.get("to", "BTC")
    amount   = request.args.get("amount", 1.0, type=float)

    # Get rates from prices
    prices = cache.get("prices_global") or {}
    rate = prices.get(f"{from_cur}/{to_cur}", {}).get("price") or prices.get(f"{to_cur}/{from_cur}", {}).get("price")

    if not rate:
        return jsonify(error="Rate not available"), 404

    return jsonify(from_currency=from_cur, to_currency=to_cur, amount=amount, result=round(amount * rate, 8))


# ──────────────────────────────────────────────────────────────
# PIP CALCULATOR
# ──────────────────────────────────────────────────────────────
@trading_bp.route("/api/pip-calculator", methods=["POST"])
def pip_calculator():
    data      = request.json
    pair      = data.get("pair", "EUR/USD")
    lot_size  = data.get("lot_size", 1.0)
    account_currency = data.get("account_currency", "USD")

    # Standard pip values (hardcoded for major pairs)
    pip_values = {
        "EUR/USD": 10.0, "GBP/USD": 10.0, "USD/JPY": 9.09,
        "USD/CHF": 9.79, "AUD/USD": 10.0, "USD/CAD": 7.52,
        "XAU/USD": 1.0,  "BTC/USDT": 1.0,
    }
    pip_value_per_lot = pip_values.get(pair, 10.0)
    result = {
        "pair": pair, "lot_size": lot_size,
        "pip_value": round(pip_value_per_lot * lot_size, 2),
        "account_currency": account_currency,
    }
    return jsonify(result)


# ──────────────────────────────────────────────────────────────
# POSITION SIZING
# ──────────────────────────────────────────────────────────────
@trading_bp.route("/api/position-size", methods=["POST"])
def position_size():
    data       = request.json
    balance    = data.get("balance", 10000.0)
    risk_pct   = data.get("risk_pct", 1.0)      # % of account
    stop_pips  = data.get("stop_pips", 20)
    pip_value  = data.get("pip_value", 10.0)    # $ per pip per lot

    risk_amount = balance * (risk_pct / 100)
    lots = risk_amount / (stop_pips * pip_value)

    return jsonify({
        "account_balance": balance,
        "risk_percent": risk_pct,
        "risk_amount_usd": round(risk_amount, 2),
        "stop_loss_pips": stop_pips,
        "recommended_lots": round(lots, 2),
        "units": round(lots * 100000),
    })


# ──────────────────────────────────────────────────────────────
# CORRELATION MATRIX
# ──────────────────────────────────────────────────────────────
@trading_bp.route("/api/correlation")
@cache.cached(timeout=3600, key_prefix="correlation_matrix")
@premium_required
def correlation_matrix():
    """Compute correlation matrix using yfinance historical data."""
    symbols = request.args.get("symbols", "BTC-USD,GC=F,EURUSD=X").split(",")
    try:
        import yfinance as yf
        import pandas as pd

        data = {}
        for sym in symbols:
            try:
                ticker = yf.Ticker(sym)
                hist   = ticker.history(period="30d")["Close"]
                data[sym] = hist
            except Exception:
                pass

        if len(data) < 2:
            return jsonify(error="Not enough data"), 400

        df   = pd.DataFrame(data).dropna()
        corr = df.corr().round(3)
        return jsonify(matrix=corr.to_dict(), symbols=list(corr.columns))
    except Exception as e:
        return jsonify(error=str(e)), 500


# ──────────────────────────────────────────────────────────────
# TRADING JOURNAL
# ──────────────────────────────────────────────────────────────
@trading_bp.route("/journal")
@login_required
def trading_journal():
    page = request.args.get("page", 1, type=int)
    trades = TradingJournal.query.filter_by(user_id=current_user.id).order_by(
        TradingJournal.opened_at.desc()
    ).paginate(page=page, per_page=20, error_out=False)

    summary = _get_pnl_summary(current_user.id)
    return render_template("trading/journal.html", trades=trades, summary=summary)


@trading_bp.route("/journal/add", methods=["POST"])
@login_required
@limiter.limit("30 per hour")
def add_trade():
    data = request.json

    trade = TradingJournal(
        user_id       = current_user.id,
        symbol        = data.get("symbol", "").upper(),
        direction     = data.get("direction"),
        entry_price   = float(data.get("entry_price", 0)),
        exit_price    = float(data["exit_price"]) if data.get("exit_price") else None,
        stop_loss     = float(data["stop_loss"])  if data.get("stop_loss")  else None,
        take_profit   = float(data["take_profit"])if data.get("take_profit")else None,
        position_size = float(data.get("position_size", 1.0)),
        leverage      = float(data.get("leverage", 1.0)),
        setup_notes   = data.get("setup_notes", ""),
        outcome_notes = data.get("outcome_notes", ""),
        timeframe     = data.get("timeframe", ""),
        session       = data.get("session", ""),
        tags          = data.get("tags", []),
        is_paper      = bool(data.get("is_paper", True)),
        opened_at     = datetime.fromisoformat(data.get("opened_at", datetime.now(timezone.utc).isoformat())),
    )

    if trade.exit_price:
        multiplier = 1 if trade.direction == "long" else -1
        trade.pnl     = multiplier * (trade.exit_price - trade.entry_price) * trade.position_size * trade.leverage
        trade.pnl_pct = (trade.pnl / (trade.entry_price * trade.position_size)) * 100
        trade.is_win  = trade.pnl > 0
        trade.closed_at = datetime.now(timezone.utc)

    db.session.add(trade)
    current_user.add_xp(10)
    db.session.commit()
    return jsonify(success=True, trade_id=trade.id)


@trading_bp.route("/journal/<int:trade_id>", methods=["PUT"])
@login_required
def update_trade(trade_id: int):
    trade = TradingJournal.query.filter_by(id=trade_id, user_id=current_user.id).first_or_404()
    data  = request.json

    if data.get("exit_price"):
        trade.exit_price  = float(data["exit_price"])
        trade.closed_at   = datetime.now(timezone.utc)
        multiplier = 1 if trade.direction == "long" else -1
        trade.pnl     = multiplier * (trade.exit_price - trade.entry_price) * trade.position_size * trade.leverage
        trade.pnl_pct = (trade.pnl / (trade.entry_price * trade.position_size)) * 100
        trade.is_win  = trade.pnl > 0

    trade.outcome_notes = data.get("outcome_notes", trade.outcome_notes)
    trade.tags          = data.get("tags", trade.tags)
    db.session.commit()
    return jsonify(success=True)


@trading_bp.route("/journal/<int:trade_id>", methods=["DELETE"])
@login_required
def delete_trade(trade_id: int):
    trade = TradingJournal.query.filter_by(id=trade_id, user_id=current_user.id).first_or_404()
    db.session.delete(trade)
    db.session.commit()
    return jsonify(success=True)


def _get_pnl_summary(user_id: int) -> dict:
    trades = TradingJournal.query.filter_by(user_id=user_id).all()
    closed = [t for t in trades if t.pnl is not None]
    wins   = [t for t in closed if t.is_win]

    total_pnl = sum(t.pnl for t in closed) if closed else 0
    win_rate  = (len(wins) / len(closed) * 100) if closed else 0
    avg_win   = sum(t.pnl for t in wins) / len(wins) if wins else 0
    losses    = [t for t in closed if not t.is_win]
    avg_loss  = sum(t.pnl for t in losses) / len(losses) if losses else 0
    profit_factor = abs(avg_win / avg_loss) if avg_loss else None

    return {
        "total_trades": len(trades),
        "closed_trades": len(closed),
        "win_rate": round(win_rate, 1),
        "total_pnl": round(total_pnl, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor else "N/A",
        "best_trade": max((t.pnl for t in closed), default=0),
        "worst_trade": min((t.pnl for t in closed), default=0),
    }


# ──────────────────────────────────────────────────────────────
# PRICE ALERTS
# ──────────────────────────────────────────────────────────────
@trading_bp.route("/alerts")
@login_required
def price_alerts():
    alerts = PriceAlert.query.filter_by(user_id=current_user.id).order_by(PriceAlert.created_at.desc()).all()
    return render_template("trading/alerts.html", alerts=alerts)


@trading_bp.route("/alerts/create", methods=["POST"])
@login_required
@limiter.limit("20 per hour")
def create_price_alert():
    data = request.json
    alert = PriceAlert(
        user_id      = current_user.id,
        symbol       = data.get("symbol", "").upper(),
        condition    = data.get("condition", "above"),
        target_price = float(data.get("target_price", 0)),
        is_recurring = bool(data.get("is_recurring", False)),
        channels     = data.get("channels", ["push"]),
        webhook_url  = data.get("webhook_url"),
        message      = data.get("message"),
    )
    db.session.add(alert)
    db.session.commit()
    return jsonify(success=True, alert_id=alert.id)


@trading_bp.route("/alerts/<int:alert_id>", methods=["DELETE"])
@login_required
def delete_alert(alert_id: int):
    alert = PriceAlert.query.filter_by(id=alert_id, user_id=current_user.id).first_or_404()
    db.session.delete(alert)
    db.session.commit()
    return jsonify(success=True)


# ──────────────────────────────────────────────────────────────
# BACKTESTING SIMULATOR (SMA Crossover)
# ──────────────────────────────────────────────────────────────
@trading_bp.route("/backtest", methods=["POST"])
@login_required
@premium_required
@limiter.limit("10 per hour")
def backtest():
    """Simple SMA crossover backtesting on historical data."""
    data       = request.json
    symbol     = data.get("symbol", "BTC-USD")
    fast_period= int(data.get("fast_period", 10))
    slow_period= int(data.get("slow_period", 30))
    period     = data.get("period", "1y")
    initial_capital = float(data.get("initial_capital", 10000))

    try:
        import yfinance as yf
        import pandas as pd

        df = yf.Ticker(symbol).history(period=period)
        if df.empty:
            return jsonify(error="No data"), 400

        df["fast_sma"] = df["Close"].rolling(fast_period).mean()
        df["slow_sma"] = df["Close"].rolling(slow_period).mean()
        df["signal"]   = 0
        df.loc[df["fast_sma"] > df["slow_sma"], "signal"] = 1
        df.loc[df["fast_sma"] < df["slow_sma"], "signal"] = -1
        df["position"]  = df["signal"].diff()

        capital  = initial_capital
        shares   = 0.0
        trades   = []

        for i, row in df.iterrows():
            if row["position"] == 2 and capital > 0:  # Buy signal
                shares  = capital / row["Close"]
                capital = 0
                trades.append({"date": str(i.date()), "type": "buy", "price": round(row["Close"], 2)})
            elif row["position"] == -2 and shares > 0:  # Sell signal
                capital = shares * row["Close"]
                shares  = 0
                trades.append({"date": str(i.date()), "type": "sell", "price": round(row["Close"], 2), "portfolio": round(capital, 2)})

        final_value = capital + shares * df["Close"].iloc[-1]
        returns     = ((final_value - initial_capital) / initial_capital) * 100

        wins  = [t for t in trades if t.get("type") == "sell" and t.get("portfolio", 0) > initial_capital]
        total_sells = [t for t in trades if t.get("type") == "sell"]

        return jsonify({
            "symbol": symbol,
            "fast_period": fast_period,
            "slow_period": slow_period,
            "initial_capital": initial_capital,
            "final_value": round(final_value, 2),
            "total_return_pct": round(returns, 2),
            "total_trades": len(total_sells),
            "win_rate": round(len(wins) / len(total_sells) * 100, 1) if total_sells else 0,
            "trades": trades[-20:],  # Last 20
        })

    except Exception as e:
        return jsonify(error=str(e)), 500


# ──────────────────────────────────────────────────────────────
# PAPER TRADING COMPETITIONS
# ──────────────────────────────────────────────────────────────
@trading_bp.route("/arena")
@login_required
def trading_arena():
    competitions = TradingCompetition.query.filter_by(is_active=True).all()
    active_comp  = TradingCompetition.query.filter(
        TradingCompetition.is_activ
