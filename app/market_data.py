import requests


BASE_URLS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
]


class MarketDataError(Exception):
    pass


def _get_json(path, params=None, timeout=10):
    last_error = None

    for base_url in BASE_URLS:
        try:
            response = requests.get(
                f"{base_url}{path}",
                params=params,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc

    raise MarketDataError(f"Impossible de récupérer les données marché: {last_error}")


def get_recent_closes(symbol="BTCUSDT", interval="1m", limit=30):
    data = _get_json(
        "/api/v3/klines",
        params={
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        },
    )

    closes = [float(kline[4]) for kline in data]

    if len(closes) < 20:
        raise MarketDataError("Pas assez de bougies pour calculer MA10 / MA20")

    return closes


def get_latest_price(symbol="BTCUSDT"):
    data = _get_json(
        "/api/v3/ticker/price",
        params={"symbol": symbol},
    )

    if "price" not in data:
        raise MarketDataError("Réponse prix invalide")

    return float(data["price"])