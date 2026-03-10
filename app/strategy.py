"""
strategy.py — Stratégie multi-signal : SMA + RSI + MACD + Bollinger Bands

Système de votes pondérés :
  SMA crossover  → poids 1
  RSI            → poids 2  (signal de retournement fort)
  MACD           → poids 2  (momentum)
  Bollinger      → poids 1  (volatilité)
  Total max      → 6 points

Score = (votes_gagnants / total_weight) * 100
Strong = score >= 70
"""
import math
from typing import Optional


# ─── INDICATEURS DE BASE ─────────────────────────────────────────────────────

def sma(prices: list, period: int) -> Optional[float]:
    """Simple Moving Average sur les N derniers prix."""
    if not prices or len(prices) < period or period <= 0:
        return None
    return round(sum(prices[-period:]) / period, 2)


def ema(prices: list, period: int) -> Optional[float]:
    """Exponential Moving Average."""
    if not prices or len(prices) < period or period <= 0:
        return None
    k = 2 / (period + 1)
    value = sum(prices[:period]) / period
    for price in prices[period:]:
        value = price * k + value * (1 - k)
    return round(value, 4)


def _ema_series(prices: list, period: int) -> list:
    """Retourne la série complète des valeurs EMA (usage interne MACD)."""
    if not prices or len(prices) < period:
        return []
    k = 2 / (period + 1)
    values = [sum(prices[:period]) / period]
    for price in prices[period:]:
        values.append(price * k + values[-1] * (1 - k))
    return values


def rsi(prices: list, period: int = 14) -> Optional[float]:
    """
    Relative Strength Index.
    RSI < 30  → survente  (signal BUY)
    RSI > 70  → surachat  (signal SELL)
    RSI = 50  → neutre    (prix plats)

    FIX : avg_gain == avg_loss == 0 (prix plats) → 50.0, pas 100.
    """
    if not prices or len(prices) < period + 1:
        return None
    deltas   = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    recent   = deltas[-period:]
    avg_gain = sum(d for d in recent if d > 0) / period
    avg_loss = sum(-d for d in recent if d < 0) / period

    if avg_gain == 0 and avg_loss == 0:
        return 50.0   # ← FIX : prix plats → neutre

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def macd(prices: list, fast: int = 12, slow: int = 26,
         signal_period: int = 9) -> Optional[dict]:
    """
    MACD = EMA(fast) - EMA(slow)
    Signal = EMA(MACD, signal_period)
    Histogram = MACD - Signal

    Histogram > 0 → momentum haussier (BUY)
    Histogram < 0 → momentum baissier (SELL)

    FIX : séries EMA alignées correctement avant de calculer MACD.
    """
    if not prices or len(prices) < slow + signal_period:
        return None

    fast_series = _ema_series(prices, fast)
    slow_series = _ema_series(prices, slow)

    if not fast_series or not slow_series:
        return None

    # slow_series[0] ↔ index (slow-1) dans prices
    # fast_series[0] ↔ index (fast-1) dans prices
    # → décalage = slow - fast
    offset = slow - fast
    if offset >= len(fast_series):
        return None

    macd_series = [
        fast_series[offset + i] - slow_series[i]
        for i in range(len(slow_series))
    ]

    if len(macd_series) < signal_period:
        return None

    # Signal line = EMA de la série MACD
    sig_k   = 2 / (signal_period + 1)
    sig_val = sum(macd_series[:signal_period]) / signal_period
    for m in macd_series[signal_period:]:
        sig_val = m * sig_k + sig_val * (1 - sig_k)

    macd_line   = round(macd_series[-1], 4)
    signal_line = round(sig_val, 4)
    histogram   = round(macd_line - signal_line, 4)

    return {
        "macd":      macd_line,
        "signal":    signal_line,
        "histogram": histogram,
    }


def bollinger_bands(prices: list, period: int = 20,
                    num_std: float = 2.0) -> Optional[dict]:
    """
    Bollinger Bands.
    Prix < lower  → survente (BUY)
    Prix > upper  → surachat (SELL)
    """
    if not prices or len(prices) < period:
        return None
    recent   = prices[-period:]
    middle   = sum(recent) / period
    variance = sum((p - middle) ** 2 for p in recent) / period
    std      = math.sqrt(variance)
    return {
        "upper":  round(middle + num_std * std, 2),
        "middle": round(middle, 2),
        "lower":  round(middle - num_std * std, 2),
    }


# ─── ANALYSE MULTI-SIGNAL ────────────────────────────────────────────────────

def analyze(prices: list) -> dict:
    """
    Analyse multi-signal combinant SMA, RSI, MACD et Bollinger Bands.

    Returns:
        {
            "signal":    "BUY" | "SELL" | "HOLD",
            "score":     int (0-100),
            "strong":    bool (True si score >= 70),
            "ma10":      float | None,
            "ma20":      float | None,
            "rsi":       float | None,
            "macd":      dict | None,
            "bollinger": dict | None,
        }
    """
    base = {
        "signal": "HOLD", "score": 0, "strong": False,
        "ma10": None, "ma20": None,
        "rsi": None, "macd": None, "bollinger": None,
    }

    if not prices or len(prices) < 2:
        return base

    current_price = prices[-1]
    ma10     = sma(prices, period=10)
    ma20     = sma(prices, period=20)
    rsi_val  = rsi(prices, period=14)
    macd_val = macd(prices)
    # FIX : keyword arg → les mocks lambda p, **kw fonctionnent
    bb       = bollinger_bands(prices, period=20)

    votes_buy    = 0
    votes_sell   = 0
    total_weight = 0

    # ── 1. SMA crossover (poids 1) ──────────────────────
    if ma10 is not None and ma20 is not None:
        total_weight += 1
        if ma10 > ma20:
            votes_buy += 1
        elif ma10 < ma20:
            votes_sell += 1

    # ── 2. RSI (poids 2) ────────────────────────────────
    if rsi_val is not None:
        total_weight += 2
        if rsi_val < 30:
            votes_buy += 2       # survente → achat
        elif rsi_val > 70:
            votes_sell += 2      # surachat → vente
        # 30 ≤ RSI ≤ 70 → neutre, pas de vote

    # ── 3. MACD (poids 2) ───────────────────────────────
    if macd_val is not None:
        total_weight += 2
        if macd_val["histogram"] > 0:
            votes_buy += 2
        elif macd_val["histogram"] < 0:
            votes_sell += 2

    # ── 4. Bollinger Bands (poids 1) ────────────────────
    if bb is not None:
        total_weight += 1
        if current_price < bb["lower"]:
            votes_buy += 1
        elif current_price > bb["upper"]:
            votes_sell += 1

    # ── Score final ─────────────────────────────────────
    if total_weight == 0:
        return {**base, "ma10": ma10, "ma20": ma20, "rsi": rsi_val,
                "macd": macd_val, "bollinger": bb}

    if votes_buy > votes_sell:
        signal = "BUY"
        score  = round((votes_buy / total_weight) * 100)
    elif votes_sell > votes_buy:
        signal = "SELL"
        score  = round((votes_sell / total_weight) * 100)
    else:
        signal = "HOLD"
        score  = 0

    if signal != "HOLD":
        score = max(score, 50)

    return {
        "signal":    signal,
        "score":     score,
        "strong":    score >= 70,
        "ma10":      ma10,
        "ma20":      ma20,
        "rsi":       rsi_val,
        "macd":      macd_val,
        "bollinger": bb,
    }