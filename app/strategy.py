def sma(values, period):
    """Calcule la moyenne mobile simple sur `period` éléments."""
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def analyze(prices):
    """
    Analyse une liste de prix de clôture et retourne un signal de trading.

    Critères du signal :
    - Croisement MA10 / MA20      → +50 points
    - Momentum des 3 dernières bougies dans la direction du signal → +30 points
    - Distance MA10/MA20 > 0.15%  → +20 points (confirmation de la force)

    Signal considéré "fort" (strong=True) si score >= 70.
    """
    ma10 = sma(prices, 10)
    ma20 = sma(prices, 20)

    if ma10 is None or ma20 is None:
        return {
            "signal": "HOLD",
            "score":  0,
            "strong": False,
            "ma10":   None,
            "ma20":   None,
        }

    # ── Direction principale ──────────────────────────────────────────────
    if ma10 > ma20:
        signal = "BUY"
    elif ma10 < ma20:
        signal = "SELL"
    else:
        signal = "HOLD"

    # ── Score de confiance ────────────────────────────────────────────────
    score = 0

    if signal != "HOLD":
        # +50 : croisement MA détecté
        score += 50

        # +30 : momentum des 3 dernières bougies confirme la direction
        if len(prices) >= 3:
            last3 = prices[-3:]
            if signal == "BUY"  and last3[2] > last3[1] > last3[0]:
                score += 30
            elif signal == "SELL" and last3[2] < last3[1] < last3[0]:
                score += 30

        # +20 : distance entre MA suffisante (signal plus fiable)
        distance_pct = abs(ma10 - ma20) / ma20 * 100
        if distance_pct > 0.15:
            score += 20

    return {
        "signal": signal,
        "score":  score,
        "strong": score >= 70,
        "ma10":   round(ma10, 4),
        "ma20":   round(ma20, 4),
    }