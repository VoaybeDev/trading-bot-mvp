"""
test_bot.py — Tests unitaires pour app/bot.py
Placez ce fichier dans : trading-bot-mvp/tests/test_bot.py
"""
import pytest
import time
from app.market_data import MarketDataError


# ─── INIT ─────────────────────────────────────────────────────────────────────

class TestBotInit:
    def test_bot_demarre_arrete(self, bot):
        assert bot.running is False

    def test_settings_charges(self, bot):
        assert bot.symbol          == "BTCUSDT"
        assert bot.interval        == "1m"
        assert bot.take_profit_usd == 1.0
        assert bot.stop_loss_usd   == -1.0
        assert bot.initial_balance == 8.0

    def test_prix_initialise(self, bot):
        assert bot.current_price == 50000.0

    def test_signal_initialise(self, bot):
        assert bot.last_signal is not None
        assert "signal" in bot.last_signal

    def test_compteur_erreurs_zero(self, bot):
        assert bot._consecutive_errors == 0


# ─── SNAPSHOT ─────────────────────────────────────────────────────────────────

class TestBotSnapshot:
    def test_snapshot_contient_toutes_les_cles(self, bot):
        snap = bot.snapshot()
        for key in ("running", "market", "settings", "last_signal",
                    "wallet", "trades", "logs", "health"):
            assert key in snap

    def test_snapshot_health(self, bot):
        snap = bot.snapshot()
        assert snap["health"]["consecutive_errors"]     == 0
        assert snap["health"]["max_consecutive_errors"] == 5

    def test_snapshot_market(self, bot):
        snap = bot.snapshot()
        assert snap["market"]["symbol"]        == "BTCUSDT"
        assert snap["market"]["current_price"] == 50000.0


# ─── TICK ─────────────────────────────────────────────────────────────────────

class TestBotTick:

    def _noop_refresh(self):
        pass

    def test_tick_sans_position_ni_signal_fort(self, bot):
        bot.last_signal = {"signal": "HOLD", "score": 0, "strong": False,
                           "ma10": None, "ma20": None}
        bot._refresh_market = self._noop_refresh
        bot.tick()
        assert not bot.wallet.has_position()

    def test_tick_ouvre_position_sur_buy_fort(self, bot):
        bot.last_signal = {"signal": "BUY", "score": 100, "strong": True,
                           "ma10": 50100.0, "ma20": 50000.0}
        bot._refresh_market = self._noop_refresh
        bot.tick()
        assert bot.wallet.has_position()

    def test_tick_ferme_position_take_profit(self, bot):
        bot.wallet.open_long(50000.0)
        qty = bot.wallet.position_qty
        bot.current_price = 50000.0 + (bot.take_profit_usd / qty) + 0.01
        bot._refresh_market = self._noop_refresh
        bot.last_signal = {"signal": "HOLD", "score": 0, "strong": False,
                           "ma10": None, "ma20": None}
        bot.tick()
        assert not bot.wallet.has_position()

    def test_tick_ferme_position_stop_loss_et_stoppe_bot(self, bot):
        bot.running = True
        bot.wallet.open_long(50000.0)
        qty = bot.wallet.position_qty
        bot.current_price = 50000.0 - (abs(bot.stop_loss_usd) / qty) - 0.01
        bot._refresh_market = self._noop_refresh
        bot.last_signal = {"signal": "HOLD", "score": 0, "strong": False,
                           "ma10": None, "ma20": None}
        bot.tick()
        assert not bot.wallet.has_position()
        assert bot.running is False

    def test_tick_gere_erreur_marche(self, bot, monkeypatch):
        """Erreur reseau : patch au niveau module pour que _refresh_market
        incremente _consecutive_errors avant de remonter l'exception."""
        import app.bot as bot_module
        monkeypatch.setattr(bot_module, "get_latest_price",
                            lambda symbol: (_ for _ in ()).throw(MarketDataError("timeout")))
        monkeypatch.setattr(time, "sleep", lambda s: None)

        initial_errors = bot._consecutive_errors
        bot.tick()
        assert bot._consecutive_errors == initial_errors + 1

    def test_tick_stoppe_bot_apres_max_erreurs(self, bot, monkeypatch):
        """Max erreurs consecutives atteint -> bot s'arrete."""
        import app.bot as bot_module
        monkeypatch.setattr(bot_module, "get_latest_price",
                            lambda symbol: (_ for _ in ()).throw(MarketDataError("down")))
        monkeypatch.setattr(time, "sleep", lambda s: None)

        bot.running = True
        bot._consecutive_errors = bot._max_consecutive_errors - 1
        bot.tick()
        assert bot.running is False


# ─── RESET ────────────────────────────────────────────────────────────────────

class TestBotReset:
    def test_reset_arrete_le_bot(self, bot):
        bot.running = True
        bot.reset()
        assert bot.running is False

    def test_reset_reinitialise_compteur_erreurs(self, bot):
        bot._consecutive_errors = 3
        bot.reset()
        assert bot._consecutive_errors == 0

    def test_reset_reinitialise_wallet(self, bot):
        bot.wallet.open_long(50000.0)
        bot.reset()
        assert not bot.wallet.has_position()
        assert bot.wallet.cash == pytest.approx(8.0)

    def test_reset_vide_les_trades(self, bot):
        from app.db import fetch_trades
        bot.wallet.open_long(50000.0)
        bot.wallet.close_long(51000.0, "TP")
        bot.reset()
        assert fetch_trades(limit=10) == []


# ─── GESTION ERREURS RÉSEAU ───────────────────────────────────────────────────

class TestBotRetry:

    def test_refresh_market_retry_puis_succes(self, bot, monkeypatch):
        """2 echecs puis succes au 3eme appel -> prix mis a jour."""
        import app.bot as bot_module
        call_count = {"n": 0}

        def flaky_price(symbol):
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise MarketDataError("timeout")
            return 51000.0

        monkeypatch.setattr(bot_module, "get_latest_price", flaky_price)
        monkeypatch.setattr(time, "sleep", lambda s: None)

        bot._consecutive_errors = 0
        bot._refresh_market()

        assert bot.current_price       == 51000.0
        assert bot._consecutive_errors == 0
        assert call_count["n"]         == 3

    def test_refresh_market_echec_total_leve_exception(self, bot, monkeypatch):
        """3 echecs consecutifs -> leve MarketDataError."""
        import app.bot as bot_module
        monkeypatch.setattr(bot_module, "get_latest_price",
                            lambda symbol: (_ for _ in ()).throw(MarketDataError("down")))
        monkeypatch.setattr(time, "sleep", lambda s: None)

        bot._consecutive_errors = 0
        with pytest.raises(MarketDataError):
            bot._refresh_market()

        assert bot._consecutive_errors == 1