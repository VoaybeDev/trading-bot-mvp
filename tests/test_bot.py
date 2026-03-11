"""
test_bot.py — Tests du TradingBot.
Fichier : trading-bot-mvp/tests/test_bot.py

Note: tick() est désormais async → les tests TestBotTick utilisent async def + await.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.bot import TradingBot
from app.market_data import MarketDataError


# ─── FIXTURES ─────────────────────────────────────────────────────────────────

def make_bot():
    """Crée un bot avec marché mocké (pas de vraie connexion Binance)."""
    with patch("app.bot.get_recent_closes", return_value=[float(i) for i in range(1, 31)]), \
         patch("app.bot.get_latest_price",  return_value=100.0), \
         patch("app.bot.analyze", return_value={
             "signal": "HOLD", "score": 0, "strong": False,
             "ma10": None, "ma20": None,
         }):
        bot = TradingBot()
    bot.current_price = 100.0
    return bot


def patch_market_ok(bot, signal="HOLD", score=0, strong=False, price=100.0):
    """Patche _refresh_market pour retourner un signal donné."""
    def _refresh():
        bot.current_price = price
        bot.last_signal   = {
            "signal": signal, "score": score,
            "strong": strong, "ma10": None, "ma20": None,
        }
        bot._consecutive_errors = 0
    return patch.object(bot, "_refresh_market", side_effect=_refresh)


def patch_market_error(bot, n_errors=1):
    """Patche _refresh_market pour lever une MarketDataError et incrémenter le compteur."""
    call_count = [0]
    def _refresh():
        call_count[0] += 1
        bot._consecutive_errors += 1
        raise MarketDataError("Simulated network error")
    return patch.object(bot, "_refresh_market", side_effect=_refresh)


# ─── TestBotInit ──────────────────────────────────────────────────────────────

class TestBotInit:

    def test_bot_demarre_arrete(self):
        bot = make_bot()
        assert bot.running is False

    def test_settings_charges(self):
        bot = make_bot()
        assert bot.symbol          == "BTCUSDT"
        assert bot.take_profit_usd  > 0
        assert bot.stop_loss_usd    < 0

    def test_prix_initialise(self):
        bot = make_bot()
        assert bot.current_price == 100.0

    def test_signal_initialise(self):
        bot = make_bot()
        assert "signal" in bot.last_signal

    def test_compteur_erreurs_zero(self):
        bot = make_bot()
        assert bot._consecutive_errors == 0

    def test_trading_mode_par_defaut_paper(self):
        bot = make_bot()
        assert bot.trading_mode == "paper"

    def test_real_position_inactif_au_demarrage(self):
        bot = make_bot()
        assert bot.real_position["active"] is False


# ─── TestBotSnapshot ──────────────────────────────────────────────────────────

class TestBotSnapshot:

    def test_snapshot_contient_toutes_les_cles(self):
        bot = make_bot()
        snap = bot.snapshot()
        for key in ("running", "market", "settings", "last_signal",
                    "wallet", "real_position", "trades", "logs", "health"):
            assert key in snap

    def test_snapshot_health(self):
        bot = make_bot()
        health = bot.snapshot()["health"]
        assert "consecutive_errors"     in health
        assert "max_consecutive_errors" in health

    def test_snapshot_market(self):
        bot = make_bot()
        market = bot.snapshot()["market"]
        assert market["symbol"]        == "BTCUSDT"
        assert market["current_price"] == 100.0

    def test_snapshot_settings_contient_trading_mode(self):
        bot = make_bot()
        settings = bot.snapshot()["settings"]
        assert "trading_mode"   in settings
        assert "order_size_pct" in settings
        assert "use_testnet"    in settings


# ─── TestBotTick (async) ──────────────────────────────────────────────────────

class TestBotTick:

    @pytest.mark.asyncio
    async def test_tick_sans_position_ni_signal_fort(self):
        bot = make_bot()
        with patch_market_ok(bot, signal="HOLD", score=0, strong=False), \
             patch("app.bot.notify_error",         new_callable=AsyncMock), \
             patch("app.bot.notify_bot_auto_stopped", new_callable=AsyncMock):
            await bot.tick()
        assert bot.wallet.has_position() is False

    @pytest.mark.asyncio
    async def test_tick_ouvre_position_sur_buy_fort(self):
        bot = make_bot()
        with patch_market_ok(bot, signal="BUY", score=83, strong=True, price=100.0), \
             patch("app.bot.notify_buy",           new_callable=AsyncMock), \
             patch("app.bot.notify_error",         new_callable=AsyncMock), \
             patch("app.bot.notify_bot_auto_stopped", new_callable=AsyncMock):
            await bot.tick()
        assert bot.wallet.has_position() is True

    @pytest.mark.asyncio
    async def test_tick_ferme_position_take_profit(self):
        bot = make_bot()
        # Ouvre une position d'abord
        with patch_market_ok(bot, signal="BUY", score=83, strong=True, price=100.0), \
             patch("app.bot.notify_buy", new_callable=AsyncMock):
            await bot.tick()

        assert bot.wallet.has_position() is True

        # Tick avec prix suffisant pour TP
        tp_price = bot.current_price + bot.take_profit_usd * 10000
        with patch_market_ok(bot, signal="HOLD", score=0, strong=False, price=tp_price), \
             patch("app.bot.notify_take_profit", new_callable=AsyncMock):
            await bot.tick()

        assert bot.wallet.has_position() is False

    @pytest.mark.asyncio
    async def test_tick_ferme_position_stop_loss_et_stoppe_bot(self):
        bot = make_bot()
        # Ouvre une position
        with patch_market_ok(bot, signal="BUY", score=83, strong=True, price=100.0), \
             patch("app.bot.notify_buy", new_callable=AsyncMock):
            await bot.tick()

        bot.running = True

        # Tick avec prix qui déclenche le SL
        sl_price = bot.current_price - bot.take_profit_usd * 10000
        with patch_market_ok(bot, signal="HOLD", score=0, strong=False, price=sl_price), \
             patch("app.bot.notify_stop_loss", new_callable=AsyncMock):
            await bot.tick()

        assert bot.wallet.has_position() is False
        assert bot.running is False

    @pytest.mark.asyncio
    async def test_tick_gere_erreur_marche(self):
        bot = make_bot()
        with patch_market_error(bot), \
             patch("app.bot.notify_error",            new_callable=AsyncMock), \
             patch("app.bot.notify_bot_auto_stopped", new_callable=AsyncMock):
            await bot.tick()
        assert bot._consecutive_errors > 0

    @pytest.mark.asyncio
    async def test_tick_stoppe_bot_apres_max_erreurs(self):
        bot = make_bot()
        bot._consecutive_errors = bot._max_consecutive_errors - 1

        with patch_market_error(bot), \
             patch("app.bot.notify_error",            new_callable=AsyncMock), \
             patch("app.bot.notify_bot_auto_stopped", new_callable=AsyncMock):
            await bot.tick()

        assert bot.running is False


# ─── TestBotReset ─────────────────────────────────────────────────────────────

class TestBotReset:

    def test_reset_arrete_le_bot(self):
        bot = make_bot()
        bot.running = True
        with patch("app.bot.get_recent_closes", return_value=[float(i) for i in range(1, 31)]), \
             patch("app.bot.get_latest_price",  return_value=100.0), \
             patch("app.bot.analyze", return_value={
                 "signal": "HOLD", "score": 0, "strong": False,
                 "ma10": None, "ma20": None,
             }):
            bot.reset()
        assert bot.running is False

    def test_reset_reinitialise_compteur_erreurs(self):
        bot = make_bot()
        bot._consecutive_errors = 5
        with patch("app.bot.get_recent_closes", return_value=[float(i) for i in range(1, 31)]), \
             patch("app.bot.get_latest_price",  return_value=100.0), \
             patch("app.bot.analyze", return_value={
                 "signal": "HOLD", "score": 0, "strong": False,
                 "ma10": None, "ma20": None,
             }):
            bot.reset()
        assert bot._consecutive_errors == 0

    def test_reset_reinitialise_wallet(self):
        bot = make_bot()
        with patch("app.bot.get_recent_closes", return_value=[float(i) for i in range(1, 31)]), \
             patch("app.bot.get_latest_price",  return_value=100.0), \
             patch("app.bot.analyze", return_value={
                 "signal": "HOLD", "score": 0, "strong": False,
                 "ma10": None, "ma20": None,
             }):
            bot.reset()
        assert bot.wallet.has_position() is False

    def test_reset_vide_les_trades(self):
        bot = make_bot()
        with patch("app.bot.get_recent_closes", return_value=[float(i) for i in range(1, 31)]), \
             patch("app.bot.get_latest_price",  return_value=100.0), \
             patch("app.bot.analyze", return_value={
                 "signal": "HOLD", "score": 0, "strong": False,
                 "ma10": None, "ma20": None,
             }):
            bot.reset()
        from app.db import fetch_trades
        assert fetch_trades(limit=100) == []

    def test_reset_reinitialise_real_position(self):
        bot = make_bot()
        bot.real_position = {
            "active": True, "entry_price": 100.0,
            "qty": 0.001,   "quote_spent": 10.0,
        }
        with patch("app.bot.get_recent_closes", return_value=[float(i) for i in range(1, 31)]), \
             patch("app.bot.get_latest_price",  return_value=100.0), \
             patch("app.bot.analyze", return_value={
                 "signal": "HOLD", "score": 0, "strong": False,
                 "ma10": None, "ma20": None,
             }):
            bot.reset()
        assert bot.real_position["active"] is False


# ─── TestBotRetry ─────────────────────────────────────────────────────────────

class TestBotRetry:

    def test_refresh_market_retry_puis_succes(self):
        bot = make_bot()
        call_count = [0]

        def flaky_closes(**kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise MarketDataError("Simulated transient error")
            return [float(i) for i in range(1, 31)]

        with patch("app.bot.get_recent_closes", side_effect=flaky_closes), \
             patch("app.bot.get_latest_price",  return_value=100.0), \
             patch("app.bot.analyze", return_value={
                 "signal": "HOLD", "score": 0, "strong": False,
                 "ma10": None, "ma20": None,
             }), \
             patch("time.sleep"):
            bot._refresh_market()

        assert bot._consecutive_errors == 0
        assert call_count[0] == 3

    def test_refresh_market_echec_total_leve_exception(self):
        bot = make_bot()
        with patch("app.bot.get_recent_closes",
                   side_effect=MarketDataError("Always fails")), \
             patch("time.sleep"):
            with pytest.raises(MarketDataError):
                bot._refresh_market()
        assert bot._consecutive_errors > 0


# ─── TestBotRealMode ──────────────────────────────────────────────────────────

class TestBotRealMode:

    @pytest.mark.asyncio
    async def test_real_mode_fallback_paper_si_non_configure(self):
        """Si les clés Binance manquent, le mode réel doit fallback sur paper."""
        bot = make_bot()
        bot.trading_mode = "real"

        with patch_market_ok(bot, signal="BUY", score=83, strong=True, price=100.0), \
             patch("app.bot.BinanceClient.is_configured", return_value=False), \
             patch("app.bot.notify_buy", new_callable=AsyncMock):
            await bot.tick()

        # Pas de position réelle ouverte (fallback paper)
        assert bot.real_position["active"] is False

    @pytest.mark.asyncio
    async def test_real_mode_ouvre_position_si_configure(self):
        bot = make_bot()
        bot.trading_mode   = "real"
        bot.order_size_pct = 100.0

        fake_order = {
            "side": "BUY", "executedQty": "0.00016",
            "fills": [{"price": "100.0", "qty": "0.00016"}],
        }

        with patch_market_ok(bot, signal="BUY", score=83, strong=True, price=100.0), \
             patch("app.bot.BinanceClient.is_configured",  return_value=True), \
             patch("app.bot.BinanceClient.get_usdt_balance",
                   new_callable=AsyncMock, return_value=10.0), \
             patch("app.bot.BinanceClient.place_market_buy",
                   new_callable=AsyncMock, return_value=fake_order), \
             patch("app.bot.notify_buy", new_callable=AsyncMock):
            await bot.tick()

        assert bot.real_position["active"]      is True
        assert bot.real_position["entry_price"] == 100.0

    @pytest.mark.asyncio
    async def test_real_mode_ferme_position_take_profit(self):
        bot = make_bot()
        bot.trading_mode    = "real"
        bot.take_profit_usd = 1.0
        bot.real_position   = {
            "active": True, "entry_price": 100.0,
            "qty": 0.001,   "quote_spent": 10.0,
        }
        # Nouveau prix → PnL = (200000 - 100) * 0.001 = beaucoup > 1.0
        bot.current_price = 2000.0

        fake_sell = {
            "side": "SELL", "executedQty": "0.001",
            "fills": [{"price": "2000.0", "qty": "0.001"}],
        }

        with patch_market_ok(bot, signal="HOLD", score=0, strong=False, price=2000.0), \
             patch("app.bot.BinanceClient.is_configured",    return_value=True), \
             patch("app.bot.BinanceClient.get_step_size",
                   new_callable=AsyncMock, return_value=0.00001), \
             patch("app.bot.BinanceClient.place_market_sell",
                   new_callable=AsyncMock, return_value=fake_sell), \
             patch("app.bot.notify_take_profit", new_callable=AsyncMock):
            await bot.tick()

        assert bot.real_position["active"] is False

    @pytest.mark.asyncio
    async def test_real_mode_solde_insuffisant(self):
        """Si le solde USDT est inférieur à 1$, aucun ordre ne doit être passé."""
        bot = make_bot()
        bot.trading_mode = "real"

        with patch_market_ok(bot, signal="BUY", score=83, strong=True, price=100.0), \
             patch("app.bot.BinanceClient.is_configured",  return_value=True), \
             patch("app.bot.BinanceClient.get_usdt_balance",
                   new_callable=AsyncMock, return_value=0.5), \
             patch("app.bot.BinanceClient.place_market_buy",
                   new_callable=AsyncMock) as mock_buy:
            await bot.tick()

        mock_buy.assert_not_called()
        assert bot.real_position["active"] is False