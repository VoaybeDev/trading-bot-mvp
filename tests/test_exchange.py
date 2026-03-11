"""
test_exchange.py — Tests du client Binance.
Fichier : trading-bot-mvp/tests/test_exchange.py
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.exchange import BinanceClient, BinanceExchangeError


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def make_resp(status: int, data: dict):
    resp = MagicMock()
    resp.status_code = status
    resp.json        = MagicMock(return_value=data)
    resp.text        = str(data)
    return resp


def mock_client_get(status: int, data: dict):
    mock = AsyncMock()
    mock.get          = AsyncMock(return_value=make_resp(status, data))
    mock.__aenter__   = AsyncMock(return_value=mock)
    mock.__aexit__    = AsyncMock(return_value=False)
    return patch("app.exchange.httpx.AsyncClient", return_value=mock)


def mock_client_post(status: int, data: dict):
    mock = AsyncMock()
    mock.post         = AsyncMock(return_value=make_resp(status, data))
    mock.__aenter__   = AsyncMock(return_value=mock)
    mock.__aexit__    = AsyncMock(return_value=False)
    return patch("app.exchange.httpx.AsyncClient", return_value=mock)


FAKE_ACCOUNT = {
    "balances": [
        {"asset": "USDT", "free": "100.00", "locked": "0.00"},
        {"asset": "BTC",  "free": "0.001",  "locked": "0.00"},
        {"asset": "ETH",  "free": "0.5",    "locked": "0.00"},
    ]
}

FAKE_ORDER_BUY = {
    "orderId": 1,
    "symbol": "BTCUSDT",
    "side": "BUY",
    "executedQty": "0.00016",
    "fills": [
        {"price": "62500.0", "qty": "0.00016", "commission": "0.0"},
    ],
}

FAKE_ORDER_SELL = {
    "orderId": 2,
    "symbol": "BTCUSDT",
    "side": "SELL",
    "executedQty": "0.00016",
    "fills": [
        {"price": "63000.0", "qty": "0.00016", "commission": "0.0"},
    ],
}

FAKE_EXCHANGE_INFO = {
    "symbols": [{
        "symbol": "BTCUSDT",
        "filters": [
            {"filterType": "LOT_SIZE", "stepSize": "0.00001"},
        ],
    }]
}


# ─── BinanceClient.__init__ ───────────────────────────────────────────────────

class TestBinanceClientInit:

    def test_testnet_url_par_defaut(self):
        client = BinanceClient(use_testnet=True)
        assert "testnet" in client.base_url

    def test_real_url_si_false(self):
        client = BinanceClient(use_testnet=False)
        assert "binance.com" in client.base_url
        assert "testnet" not in client.base_url

    def test_is_configured_false_si_pas_de_cles(self):
        with patch("app.exchange.os.getenv", return_value=""):
            client = BinanceClient()
            assert client.is_configured() is False

    def test_is_configured_true_si_cles_presentes(self):
        with patch.dict("os.environ", {
            "BINANCE_API_KEY":    "mykey",
            "BINANCE_SECRET_KEY": "mysecret",
        }):
            client = BinanceClient()
            assert client.is_configured() is True


# ─── _sign ────────────────────────────────────────────────────────────────────

class TestSign:

    def test_sign_ajoute_timestamp(self):
        with patch.dict("os.environ", {"BINANCE_SECRET_KEY": "secret"}):
            client = BinanceClient()
            params = client._sign({})
        assert "timestamp" in params

    def test_sign_ajoute_signature(self):
        with patch.dict("os.environ", {"BINANCE_SECRET_KEY": "secret"}):
            client = BinanceClient()
            params = client._sign({})
        assert "signature" in params
        assert len(params["signature"]) == 64

    def test_sign_ne_modifie_pas_les_autres_params(self):
        with patch.dict("os.environ", {"BINANCE_SECRET_KEY": "secret"}):
            client = BinanceClient()
            params = client._sign({"symbol": "BTCUSDT", "side": "BUY"})
        assert params["symbol"] == "BTCUSDT"
        assert params["side"]   == "BUY"


# ─── round_step ───────────────────────────────────────────────────────────────

class TestRoundStep:

    def test_arrondi_a_5_decimales(self):
        assert BinanceClient.round_step(0.000168, 0.00001) == pytest.approx(0.00016)

    def test_arrondi_a_2_decimales(self):
        assert BinanceClient.round_step(10.567, 0.01) == pytest.approx(10.56)

    def test_arrondi_a_entier(self):
        assert BinanceClient.round_step(1.9, 1.0) == pytest.approx(1.0)

    def test_step_zero_retourne_valeur_originale(self):
        assert BinanceClient.round_step(1.23456, 0) == pytest.approx(1.23456)

    def test_toujours_arrondi_en_dessous(self):
        assert BinanceClient.round_step(0.00019, 0.0001) == pytest.approx(0.0001)


# ─── parse_filled_qty / parse_avg_price ───────────────────────────────────────

class TestParseOrder:

    def test_parse_filled_qty(self):
        qty = BinanceClient.parse_filled_qty(FAKE_ORDER_BUY)
        assert qty == pytest.approx(0.00016)

    def test_parse_filled_qty_zero_si_absent(self):
        assert BinanceClient.parse_filled_qty({}) == 0.0

    def test_parse_avg_price(self):
        price = BinanceClient.parse_avg_price(FAKE_ORDER_BUY)
        assert price == pytest.approx(62500.0)

    def test_parse_avg_price_zero_si_pas_fills(self):
        assert BinanceClient.parse_avg_price({"fills": []}) == 0.0

    def test_parse_avg_price_moyenne_ponderee(self):
        order = {
            "fills": [
                {"price": "100.0", "qty": "1.0"},
                {"price": "200.0", "qty": "1.0"},
            ]
        }
        assert BinanceClient.parse_avg_price(order) == pytest.approx(150.0)

    def test_parse_avg_price_arrondi_8_decimales(self):
        """Vérifie que le résultat est arrondi pour éviter 62499.9999..."""
        order = {
            "fills": [{"price": "62500.0", "qty": "0.00016"}]
        }
        price = BinanceClient.parse_avg_price(order)
        assert price == pytest.approx(62500.0, rel=1e-6)


# ─── get_account ──────────────────────────────────────────────────────────────

class TestGetAccount:

    @pytest.mark.asyncio
    async def test_retourne_dict_si_succes(self):
        with mock_client_get(200, FAKE_ACCOUNT):
            client = BinanceClient()
            result = await client.get_account()
        assert "balances" in result

    @pytest.mark.asyncio
    async def test_leve_exception_si_401(self):
        with mock_client_get(401, {"msg": "Unauthorized"}):
            client = BinanceClient()
            with pytest.raises(BinanceExchangeError):
                await client.get_account()


# ─── get_usdt_balance ─────────────────────────────────────────────────────────

class TestGetUsdtBalance:

    @pytest.mark.asyncio
    async def test_retourne_balance_usdt(self):
        with mock_client_get(200, FAKE_ACCOUNT):
            balance = await BinanceClient().get_usdt_balance()
        assert balance == pytest.approx(100.0)

    @pytest.mark.asyncio
    async def test_retourne_zero_si_usdt_absent(self):
        account = {"balances": [{"asset": "BTC", "free": "1.0"}]}
        with mock_client_get(200, account):
            balance = await BinanceClient().get_usdt_balance()
        assert balance == 0.0


# ─── get_asset_balance ────────────────────────────────────────────────────────

class TestGetAssetBalance:

    @pytest.mark.asyncio
    async def test_retourne_balance_btc(self):
        with mock_client_get(200, FAKE_ACCOUNT):
            balance = await BinanceClient().get_asset_balance("BTC")
        assert balance == pytest.approx(0.001)

    @pytest.mark.asyncio
    async def test_retourne_zero_si_asset_absent(self):
        with mock_client_get(200, FAKE_ACCOUNT):
            balance = await BinanceClient().get_asset_balance("SOL")
        assert balance == 0.0


# ─── get_step_size ────────────────────────────────────────────────────────────

class TestGetStepSize:

    @pytest.mark.asyncio
    async def test_retourne_step_size_correct(self):
        with mock_client_get(200, FAKE_EXCHANGE_INFO):
            step = await BinanceClient().get_step_size("BTCUSDT")
        assert step == pytest.approx(0.00001)

    @pytest.mark.asyncio
    async def test_retourne_fallback_si_erreur(self):
        with mock_client_get(400, {}):
            step = await BinanceClient().get_step_size("BTCUSDT")
        assert step == pytest.approx(0.00001)


# ─── place_market_buy ─────────────────────────────────────────────────────────

class TestPlaceMarketBuy:

    @pytest.mark.asyncio
    async def test_retourne_ordre_si_succes(self):
        with mock_client_post(200, FAKE_ORDER_BUY):
            order = await BinanceClient().place_market_buy("BTCUSDT", 10.0)
        assert order["side"] == "BUY"

    @pytest.mark.asyncio
    async def test_leve_exception_si_400(self):
        with mock_client_post(400, {"msg": "MIN_NOTIONAL"}):
            with pytest.raises(BinanceExchangeError):
                await BinanceClient().place_market_buy("BTCUSDT", 0.001)

    @pytest.mark.asyncio
    async def test_utilise_quote_order_qty(self):
        mock = AsyncMock()
        mock.post       = AsyncMock(return_value=make_resp(200, FAKE_ORDER_BUY))
        mock.__aenter__ = AsyncMock(return_value=mock)
        mock.__aexit__  = AsyncMock(return_value=False)

        with patch("app.exchange.httpx.AsyncClient", return_value=mock):
            await BinanceClient().place_market_buy("BTCUSDT", 10.0)

        call_params = mock.post.call_args[1]["params"]
        assert "quoteOrderQty" in call_params
        assert call_params["quoteOrderQty"] == pytest.approx(10.0)


# ─── place_market_sell ────────────────────────────────────────────────────────

class TestPlaceMarketSell:

    @pytest.mark.asyncio
    async def test_retourne_ordre_si_succes(self):
        mock = AsyncMock()
        mock.get        = AsyncMock(return_value=make_resp(200, FAKE_EXCHANGE_INFO))
        mock.post       = AsyncMock(return_value=make_resp(200, FAKE_ORDER_SELL))
        mock.__aenter__ = AsyncMock(return_value=mock)
        mock.__aexit__  = AsyncMock(return_value=False)

        with patch("app.exchange.httpx.AsyncClient", return_value=mock):
            order = await BinanceClient().place_market_sell("BTCUSDT", 0.00016)

        assert order["side"] == "SELL"

    @pytest.mark.asyncio
    async def test_leve_exception_si_quantite_nulle(self):
        mock = AsyncMock()
        mock.get        = AsyncMock(return_value=make_resp(200, FAKE_EXCHANGE_INFO))
        mock.__aenter__ = AsyncMock(return_value=mock)
        mock.__aexit__  = AsyncMock(return_value=False)

        with patch("app.exchange.httpx.AsyncClient", return_value=mock):
            with pytest.raises(BinanceExchangeError):
                await BinanceClient().place_market_sell("BTCUSDT", 0.000001)