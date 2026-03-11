"""
health.py — Module de health check pour NexTrade.
"""
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from .db import DB_PATH, get_db_stats


def _check_db() -> dict:
    start = time.perf_counter()
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("SELECT 1").fetchone()
        conn.close()
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        stats = get_db_stats()
        return {
            "status":       "ok",
            "latency_ms":   latency_ms,
            "path":         str(DB_PATH),
            "size_kb":      round(Path(DB_PATH).stat().st_size / 1024, 2) if Path(DB_PATH).exists() else 0,
            "trades_count": stats["trades_count"],
            "logs_count":   stats["logs_count"],
            "max_trades":   stats["max_trades"],
            "max_logs":     stats["max_logs"],
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def _check_bot(bot) -> dict:
    return {
        "status":                 "running" if bot.running else "stopped",
        "consecutive_errors":     bot._consecutive_errors,
        "max_consecutive_errors": bot._max_consecutive_errors,
        "error_rate":             "high" if bot._consecutive_errors >= 3 else "normal",
        "current_price":          bot.current_price,
        "symbol":                 bot.symbol,
        "has_position":           bot.wallet.has_position(),
    }


def _check_wallet(bot) -> dict:
    w       = bot.wallet.status(bot.current_price)
    initial = w["initial_balance"]
    equity  = w["equity"]
    pnl_pct = round((equity - initial) / initial * 100, 2) if initial > 0 else 0.0
    return {
        "initial_balance": w["initial_balance"],
        "equity":          w["equity"],
        "cash":            w["cash"],
        "has_position":    w["has_position"],
        "daily_pnl_usd":   w["daily_pnl"],
        "daily_pnl_pct":   pnl_pct,
        "position_pnl":    w["position_pnl"],
    }


def _check_market(bot) -> dict:
    sig = bot.last_signal
    return {
        "symbol":        bot.symbol,
        "interval":      bot.interval,
        "current_price": bot.current_price,
        "signal":        sig.get("signal", "HOLD"),
        "score":         sig.get("score", 0),
        "strong":        sig.get("strong", False),
        "ma10":          sig.get("ma10"),
        "ma20":          sig.get("ma20"),
    }


def build_health_report(bot) -> dict:
    db_check     = _check_db()
    bot_check    = _check_bot(bot)
    wallet_check = _check_wallet(bot)
    market_check = _check_market(bot)

    if db_check["status"] == "error":
        overall = "error"
    elif bot_check["consecutive_errors"] >= 3:
        overall = "degraded"
    else:
        overall = "ok"

    return {
        "status":    overall,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "version":   "1.0.0",
        "components": {
            "database": db_check,
            "bot":      bot_check,
            "wallet":   wallet_check,
            "market":   market_check,
        },
    }