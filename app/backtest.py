"""
backtest.py — Moteur de backtesting pour NexTrade.
Placez ce fichier dans : trading-bot-mvp/app/backtest.py
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any

import httpx

from .strategy import analyze

BINANCE_BASE_URL = os.getenv("BINANCE_BASE_URL", "https://api.binance.com")


# ─── FETCH KLINES ─────────────────────────────────────────────────────────────

async def fetch_klines(
    symbol: str,
    interval: str,
    start_dt: datetime,
    end_dt: datetime,
) -> list[dict]:
    """
    Récupère les bougies historiques depuis l'API publique Binance.
    Retourne une liste de dicts avec open, high, low, close, volume, open_time.
    Gère la pagination automatiquement (max 1000 bougies par requête).
    """
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms   = int(end_dt.timestamp()   * 1000)

    all_klines: list[dict] = []
    current_start = start_ms

    async with httpx.AsyncClient(timeout=30) as client:
        while current_start < end_ms:
            params = {
                "symbol":    symbol.upper(),
                "interval":  interval,
                "startTime": current_start,
                "endTime":   end_ms,
                "limit":     1000,
            }
            resp = await client.get(
                f"{BINANCE_BASE_URL}/api/v3/klines",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

            if not data:
                break

            for k in data:
                all_klines.append({
                    "open_time": k[0],
                    "open":      float(k[1]),
                    "high":      float(k[2]),
                    "low":       float(k[3]),
                    "close":     float(k[4]),
                    "volume":    float(k[5]),
                })

            # Pagination : on repart depuis la dernière bougie + 1ms
            last_open_time = data[-1][0]
            if last_open_time <= current_start:
                break
            current_start = last_open_time + 1

    return all_klines


# ─── BACKTEST ENGINE ──────────────────────────────────────────────────────────

def run_backtest(
    klines: list[dict],
    initial_balance: float = 8.0,
    take_profit_usd: float = 1.0,
    stop_loss_usd: float = -1.0,
) -> dict[str, Any]:
    """
    Rejoue la stratégie multi-signal sur les bougies historiques.

    Règles :
    - On entre en LONG dès que signal == "BUY" et strong == True
    - On sort sur TP, SL, ou signal SELL
    - Une seule position à la fois
    - On investit 100% du cash disponible à chaque entrée

    Retourne un dict avec métriques et equity_curve.
    """
    if len(klines) < 25:
        return _empty_result(initial_balance)

    closes      = [k["close"] for k in klines]
    equity      = initial_balance
    cash        = initial_balance
    position    = None   # {"entry_price": float, "qty": float, "equity_at_entry": float}
    trades: list[dict] = []
    equity_curve: list[dict] = []
    peak_equity = initial_balance

    for i in range(20, len(klines)):
        price   = closes[i]
        history = closes[: i + 1]
        ts      = klines[i]["open_time"]

        # ── Si position ouverte : vérifier TP/SL/SELL ──
        if position is not None:
            entry  = position["entry_price"]
            qty    = position["qty"]
            pnl    = (price - entry) * qty

            should_close = False
            reason       = ""

            if pnl >= take_profit_usd:
                should_close = True
                reason = "TP"
            elif pnl <= stop_loss_usd:
                should_close = True
                reason = "SL"
            else:
                sig = analyze(history)
                if sig["signal"] == "SELL":
                    should_close = True
                    reason = "SELL"

            if should_close:
                cash  = position["qty"] * price
                equity = cash
                trades.append({
                    "entry_price": round(entry, 4),
                    "exit_price":  round(price, 4),
                    "quantity":    round(qty, 6),
                    "pnl":         round(pnl, 4),
                    "reason":      reason,
                    "open_time":   position["open_time"],
                    "close_time":  ts,
                })
                position = None

        # ── Si pas de position : chercher entrée BUY ──
        elif cash > 0:
            sig = analyze(history)
            if sig["signal"] == "BUY" and sig.get("strong", False):
                qty      = cash / price
                position = {
                    "entry_price": price,
                    "qty":         qty,
                    "open_time":   ts,
                }
                cash = 0.0

        # ── Calcul equity courante ──
        if position is not None:
            current_equity = position["qty"] * price
        else:
            current_equity = cash

        if current_equity > peak_equity:
            peak_equity = current_equity

        equity_curve.append({
            "ts":     ts,
            "equity": round(current_equity, 4),
        })

    # ── Fermer position encore ouverte au dernier prix ──
    if position is not None:
        last_price = closes[-1]
        qty  = position["qty"]
        pnl  = (last_price - position["entry_price"]) * qty
        cash = qty * last_price
        trades.append({
            "entry_price": round(position["entry_price"], 4),
            "exit_price":  round(last_price, 4),
            "quantity":    round(qty, 6),
            "pnl":         round(pnl, 4),
            "reason":      "END",
            "open_time":   position["open_time"],
            "close_time":  klines[-1]["open_time"],
        })
        equity = cash

    # ── Métriques ──
    final_equity   = round(equity, 4)
    total_pnl_usd  = round(final_equity - initial_balance, 4)
    total_pnl_pct  = round((total_pnl_usd / initial_balance) * 100, 2) if initial_balance else 0.0
    winning_trades = [t for t in trades if t["pnl"] > 0]
    losing_trades  = [t for t in trades if t["pnl"] <= 0]
    win_rate       = round(len(winning_trades) / len(trades) * 100, 1) if trades else 0.0

    # Max drawdown
    running_peak   = initial_balance
    max_drawdown   = 0.0
    for point in equity_curve:
        e = point["equity"]
        if e > running_peak:
            running_peak = e
        dd = (running_peak - e) / running_peak * 100 if running_peak else 0
        if dd > max_drawdown:
            max_drawdown = dd

    avg_win  = round(sum(t["pnl"] for t in winning_trades) / len(winning_trades), 4) if winning_trades else 0.0
    avg_loss = round(sum(t["pnl"] for t in losing_trades)  / len(losing_trades),  4) if losing_trades  else 0.0

    return {
        "initial_balance":   initial_balance,
        "final_equity":      final_equity,
        "total_pnl_usd":     total_pnl_usd,
        "total_pnl_pct":     total_pnl_pct,
        "total_trades":      len(trades),
        "winning_trades":    len(winning_trades),
        "losing_trades":     len(losing_trades),
        "win_rate":          win_rate,
        "max_drawdown_pct":  round(max_drawdown, 2),
        "avg_win_usd":       avg_win,
        "avg_loss_usd":      avg_loss,
        "klines_count":      len(klines),
        "equity_curve":      equity_curve,
        "trades":            trades,
    }


def _empty_result(initial_balance: float) -> dict:
    return {
        "initial_balance":  initial_balance,
        "final_equity":     initial_balance,
        "total_pnl_usd":    0.0,
        "total_pnl_pct":    0.0,
        "total_trades":     0,
        "winning_trades":   0,
        "losing_trades":    0,
        "win_rate":         0.0,
        "max_drawdown_pct": 0.0,
        "avg_win_usd":      0.0,
        "avg_loss_usd":     0.0,
        "klines_count":     0,
        "equity_curve":     [],
        "trades":           [],
    }