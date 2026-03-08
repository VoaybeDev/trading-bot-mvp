def sma(values, period):
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def analyze(prices):
    ma10 = sma(prices, 10)
    ma20 = sma(prices, 20)

    if ma10 is None or ma20 is None:
        return {
            "signal": "HOLD",
            "score": 0,
            "strong": False,
            "ma10": None,
            "ma20": None,
        }

    if ma10 > ma20:
        signal = "BUY"
    elif ma10 < ma20:
        signal = "SELL"
    else:
        signal = "HOLD"

    score = 0

    if signal != "HOLD":
        score += 50

    last3 = prices[-3:]
    if signal == "BUY" and last3[2] > last3[1] > last3[0]:
        score += 30
    elif signal == "SELL" and last3[2] < last3[1] < last3[0]:
        score += 30

    distance_pct = abs(ma10 - ma20) / ma20 * 100
    if distance_pct > 0.15:
        score += 20

    return {
        "signal": signal,
        "score": score,
        "strong": score >= 70,
        "ma10": round(ma10, 4),
        "ma20": round(ma20, 4),
    }