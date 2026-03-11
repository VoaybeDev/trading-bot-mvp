"""
test_backtest.py — Tests du moteur de backtesting NexTrade.
Placez ce fichier dans : trading-bot-mvp/tests/test_backtest.py
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.backtest import run_backtest, fetch_klines, _empty_result


# ─── FIXTURES ─────────────────────────────────────────────────────────────────

def make_klines(n: int, base_price: float = 50000.0) -> list[dict]:
    """Génère n bougies avec prix constant."""
    return [
        {
            "open_time": i * 60000,
            "open":      base_price,
            "high":      base_price * 1.001,
            "low":       base_price * 0.999,
            "close":     base_price,
            "volume":    1.0,
        }
        for i in range(n)
    ]


def make_klines_trending_up(n: int = 60) -> list[dict]:
    """Bougies avec tendance haussière marquée."""
    klines = []
    for i in range(n):
        price = 50000.0 + i * 100
        klines.append({
            "open_time": i * 60000,
            "open":  price,
            "high":  price * 1.002,
            "low":   price * 0.998,
            "close": price,
            "volume": 1.0,
        })
    return klines


def make_klines_trending_down(n: int = 60) -> list[dict]:
    """Bougies avec tendance baissière marquée."""
    klines = []
    for i in range(n):
        price = 55000.0 - i * 100
        klines.append({
            "open_time": i * 60000,
            "open":  price,
            "high":  price * 1.001,
            "low":   price * 0.999,
            "close": price,
            "volume": 1.0,
        })
    return klines


BINANCE_KLINES_RESPONSE = [
    [
        1700000000000,  # open_time
        "50000.0",      # open
        "50100.0",      # high
        "49900.0",      # low
        "50050.0",      # close
        "10.5",         # volume
        1700000059999,  # close_time
        "525000.0",     # quote_volume
        100,            # trades
        "5.0",          # taker_buy_base
        "250000.0",     # taker_buy_quote
        "0",            # ignore
    ]
    for _ in range(50)
]


# ─── run_backtest ──────────────────────────────────────────────────────────────

class TestRunBacktest:

    def test_retourne_dict_avec_toutes_les_cles(self):
        klines = make_klines(50)
        result = run_backtest(klines)
        expected_keys = [
            "initial_balance", "final_equity", "total_pnl_usd",
            "total_pnl_pct", "total_trades", "winning_trades",
            "losing_trades", "win_rate", "max_drawdown_pct",
            "avg_win_usd", "avg_loss_usd", "klines_count",
            "equity_curve", "trades",
        ]
        for key in expected_keys:
            assert key in result, f"Clé manquante: {key}"

    def test_equity_curve_non_vide(self):
        klines = make_klines(50)
        result = run_backtest(klines)
        assert isinstance(result["equity_curve"], list)
        assert len(result["equity_curve"]) > 0

    def test_equity_curve_a_ts_et_equity(self):
        klines = make_klines(50)
        result = run_backtest(klines)
        for point in result["equity_curve"]:
            assert "ts"     in point
            assert "equity" in point

    def test_initial_balance_respecte(self):
        klines = make_klines(50)
        result = run_backtest(klines, initial_balance=100.0)
        assert result["initial_balance"] == 100.0

    def test_klines_insuffisantes_retourne_empty(self):
        klines = make_klines(10)  # < 25
        result = run_backtest(klines)
        assert result["total_trades"] == 0
        assert result["final_equity"] == result["initial_balance"]
        assert result["equity_curve"] == []

    def test_exactly_25_klines_ok(self):
        klines = make_klines(25)
        result = run_backtest(klines)
        assert isinstance(result, dict)

    def test_total_pnl_coherent(self):
        klines = make_klines(50)
        result = run_backtest(klines)
        expected_pnl = round(result["final_equity"] - result["initial_balance"], 4)
        assert result["total_pnl_usd"] == expected_pnl

    def test_total_pnl_pct_coherent(self):
        klines = make_klines(50)
        result = run_backtest(klines, initial_balance=8.0)
        expected_pct = round((result["total_pnl_usd"] / 8.0) * 100, 2)
        assert result["total_pnl_pct"] == expected_pct

    def test_win_rate_zero_si_aucun_trade(self):
        klines = make_klines(50)
        result = run_backtest(klines)
        if result["total_trades"] == 0:
            assert result["win_rate"] == 0.0

    def test_win_rate_entre_0_et_100(self):
        klines = make_klines_trending_up(100)
        result = run_backtest(klines)
        assert 0.0 <= result["win_rate"] <= 100.0

    def test_max_drawdown_positif_ou_zero(self):
        klines = make_klines(50)
        result = run_backtest(klines)
        assert result["max_drawdown_pct"] >= 0.0

    def test_max_drawdown_inferieur_100(self):
        klines = make_klines_trending_down(100)
        result = run_backtest(klines)
        assert result["max_drawdown_pct"] <= 100.0

    def test_winning_plus_losing_egale_total(self):
        klines = make_klines_trending_up(100)
        result = run_backtest(klines)
        assert result["winning_trades"] + result["losing_trades"] == result["total_trades"]

    def test_trades_sont_des_dicts(self):
        klines = make_klines_trending_up(100)
        result = run_backtest(klines)
        for trade in result["trades"]:
            assert "entry_price" in trade
            assert "exit_price"  in trade
            assert "pnl"         in trade
            assert "reason"      in trade

    def test_reason_valide(self):
        klines = make_klines_trending_up(100)
        result = run_backtest(klines)
        valid_reasons = {"TP", "SL", "SELL", "END"}
        for trade in result["trades"]:
            assert trade["reason"] in valid_reasons

    def test_klines_count_correct(self):
        klines = make_klines(50)
        result = run_backtest(klines)
        assert result["klines_count"] == 50

    def test_capital_8_dollars(self):
        klines = make_klines(50)
        result = run_backtest(klines, initial_balance=8.0)
        assert result["initial_balance"] == 8.0

    def test_take_profit_custom(self):
        klines = make_klines_trending_up(200)
        result = run_backtest(klines, initial_balance=100.0, take_profit_usd=5.0)
        for trade in result["trades"]:
            if trade["reason"] == "TP":
                assert trade["pnl"] >= 4.5  # tolérance légère

    def test_stop_loss_custom(self):
        klines = make_klines_trending_down(200)
        result = run_backtest(klines, initial_balance=100.0, stop_loss_usd=-2.0)
        for trade in result["trades"]:
            if trade["reason"] == "SL":
                assert trade["pnl"] <= -1.5  # tolérance légère

    def test_pas_de_position_double(self):
        """On ne peut pas ouvrir 2 positions simultanées."""
        klines = make_klines_trending_up(200)
        result = run_backtest(klines)
        # Vérifie que chaque trade est bien fermé avant le suivant
        for i in range(len(result["trades"]) - 1):
            t1 = result["trades"][i]
            t2 = result["trades"][i + 1]
            assert t1["close_time"] <= t2["open_time"]

    def test_equity_toujours_positive(self):
        klines = make_klines_trending_down(100)
        result = run_backtest(klines, initial_balance=8.0, stop_loss_usd=-1.0)
        for point in result["equity_curve"]:
            assert point["equity"] >= 0

    def test_avg_win_positif_si_trades_gagnants(self):
        klines = make_klines_trending_up(100)
        result = run_backtest(klines)
        if result["winning_trades"] > 0:
            assert result["avg_win_usd"] > 0

    def test_avg_loss_negatif_ou_zero_si_trades_perdants(self):
        klines = make_klines_trending_down(100)
        result = run_backtest(klines)
        if result["losing_trades"] > 0:
            assert result["avg_loss_usd"] <= 0


# ─── _empty_result ─────────────────────────────────────────────────────────────

class TestEmptyResult:

    def test_retourne_initial_balance(self):
        r = _empty_result(8.0)
        assert r["initial_balance"] == 8.0
        assert r["final_equity"]    == 8.0

    def test_tous_les_compteurs_a_zero(self):
        r = _empty_result(8.0)
        assert r["total_trades"]   == 0
        assert r["total_pnl_usd"]  == 0.0
        assert r["equity_curve"]   == []
        assert r["trades"]         == []


# ─── fetch_klines (mocké) ──────────────────────────────────────────────────────

class TestFetchKlines:

    @pytest.mark.asyncio
    async def test_retourne_liste_de_klines(self):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value=BINANCE_KLINES_RESPONSE)
        mock_response.raise_for_status = AsyncMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)

        with patch("app.backtest.httpx.AsyncClient", return_value=mock_client):
            start = datetime(2026, 3, 1)
            end   = datetime(2026, 3, 2)
            result = await fetch_klines("BTCUSDT", "1m", start, end)

        assert isinstance(result, list)
        assert len(result) == 50

    @pytest.mark.asyncio
    async def test_klines_ont_les_bons_champs(self):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value=BINANCE_KLINES_RESPONSE)
        mock_response.raise_for_status = AsyncMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)

        with patch("app.backtest.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_klines(
                "BTCUSDT", "1m",
                datetime(2026, 3, 1),
                datetime(2026, 3, 2),
            )

        for k in result:
            assert "open_time" in k
            assert "open"      in k
            assert "high"      in k
            assert "low"       in k
            assert "close"     in k
            assert "volume"    in k

    @pytest.mark.asyncio
    async def test_close_est_float(self):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value=BINANCE_KLINES_RESPONSE)
        mock_response.raise_for_status = AsyncMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)

        with patch("app.backtest.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_klines(
                "BTCUSDT", "1m",
                datetime(2026, 3, 1),
                datetime(2026, 3, 2),
            )

        for k in result:
            assert isinstance(k["close"], float)

    @pytest.mark.asyncio
    async def test_retourne_liste_vide_si_api_vide(self):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value=[])
        mock_response.raise_for_status = AsyncMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)

        with patch("app.backtest.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_klines(
                "BTCUSDT", "1m",
                datetime(2026, 3, 1),
                datetime(2026, 3, 2),
            )

        assert result == []