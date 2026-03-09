"""
test_db.py — Tests unitaires pour app/db.py
Placez ce fichier dans : trading-bot-mvp/tests/test_db.py
"""
import pytest
from app.db import (
    fetch_logs,
    fetch_trades,
    get_db_stats,
    get_wallet_state,
    init_db,
    insert_log,
    insert_trade,
    reset_database,
    save_wallet_state,
    MAX_LOGS,
    MAX_TRADES,
)


# ─── INIT ─────────────────────────────────────────────────────────────────────

class TestInitDb:
    def test_init_cree_le_wallet(self, use_temp_db):
        init_db(initial_balance=10.0)
        state = get_wallet_state()
        assert state is not None
        assert state["initial_balance"] == 10.0
        assert state["cash"] == 10.0
        assert state["position_qty"] == 0.0
        assert state["entry_price"] is None

    def test_init_idempotente(self, use_temp_db):
        # Appeler init_db deux fois ne doit pas planter ni dupliquer
        init_db(initial_balance=8.0)
        init_db(initial_balance=8.0)
        state = get_wallet_state()
        assert state["initial_balance"] == 8.0


# ─── WALLET ───────────────────────────────────────────────────────────────────

class TestWalletState:
    def test_save_et_get_wallet(self, fresh_db):
        save_wallet_state(
            initial_balance=8.0,
            cash=5.0,
            position_qty=0.001,
            entry_price=50000.0,
        )
        state = get_wallet_state()
        assert state["cash"] == 5.0
        assert state["position_qty"] == 0.001
        assert state["entry_price"] == 50000.0

    def test_entry_price_none(self, fresh_db):
        save_wallet_state(8.0, 8.0, 0.0, None)
        state = get_wallet_state()
        assert state["entry_price"] is None


# ─── LOGS ─────────────────────────────────────────────────────────────────────

class TestLogs:
    def test_insert_et_fetch_log(self, fresh_db):
        insert_log("Test message")
        logs = fetch_logs(limit=10)
        assert len(logs) == 1
        assert logs[0]["message"] == "Test message"
        assert "created_at" in logs[0]
        assert "id" in logs[0]

    def test_fetch_logs_limite(self, fresh_db):
        for i in range(10):
            insert_log(f"Log {i}")
        logs = fetch_logs(limit=3)
        assert len(logs) == 3

    def test_fetch_logs_ordre_desc(self, fresh_db):
        insert_log("Premier")
        insert_log("Deuxieme")
        insert_log("Troisieme")
        logs = fetch_logs(limit=10)
        # Le plus récent en premier
        assert logs[0]["message"] == "Troisieme"
        assert logs[-1]["message"] == "Premier"

    def test_purge_automatique_logs(self, fresh_db):
        """La table ne doit jamais dépasser MAX_LOGS entrées."""
        # Insère MAX_LOGS + 20 logs
        for i in range(MAX_LOGS + 20):
            insert_log(f"Log {i}")

        stats = get_db_stats()
        assert stats["logs_count"] <= MAX_LOGS


# ─── TRADES ───────────────────────────────────────────────────────────────────

class TestTrades:
    def _make_trade(self, pnl=1.0):
        return {
            "side":        "LONG",
            "entry_price": 50000.0,
            "exit_price":  51000.0,
            "quantity":    0.0001,
            "pnl":         pnl,
            "reason":      "TP 1$",
        }

    def test_insert_et_fetch_trade(self, fresh_db):
        insert_trade(self._make_trade(pnl=0.5))
        trades = fetch_trades(limit=10)
        assert len(trades) == 1
        assert trades[0]["pnl"] == 0.5
        assert trades[0]["side"] == "LONG"

    def test_fetch_trades_limite(self, fresh_db):
        for i in range(10):
            insert_trade(self._make_trade(pnl=float(i)))
        trades = fetch_trades(limit=3)
        assert len(trades) == 3

    def test_fetch_trades_ordre_desc(self, fresh_db):
        insert_trade(self._make_trade(pnl=1.0))
        insert_trade(self._make_trade(pnl=2.0))
        insert_trade(self._make_trade(pnl=3.0))
        trades = fetch_trades(limit=10)
        # Le plus récent en premier
        assert trades[0]["pnl"] == 3.0
        assert trades[-1]["pnl"] == 1.0

    def test_purge_automatique_trades(self, fresh_db):
        """La table ne doit jamais dépasser MAX_TRADES entrées."""
        for i in range(MAX_TRADES + 20):
            insert_trade(self._make_trade(pnl=float(i)))

        stats = get_db_stats()
        assert stats["trades_count"] <= MAX_TRADES


# ─── STATS ────────────────────────────────────────────────────────────────────

class TestDbStats:
    def test_stats_vide(self, fresh_db):
        stats = get_db_stats()
        assert stats["trades_count"] == 0
        assert stats["logs_count"] == 0
        assert stats["max_trades"] == MAX_TRADES
        assert stats["max_logs"] == MAX_LOGS

    def test_stats_apres_insertions(self, fresh_db):
        insert_log("log1")
        insert_log("log2")
        insert_trade({
            "side": "LONG", "entry_price": 50000.0, "exit_price": 51000.0,
            "quantity": 0.0001, "pnl": 1.0, "reason": "TP",
        })
        stats = get_db_stats()
        assert stats["logs_count"] == 2
        assert stats["trades_count"] == 1


# ─── RESET ────────────────────────────────────────────────────────────────────

class TestResetDatabase:
    def test_reset_vide_les_tables(self, fresh_db):
        insert_log("log")
        insert_trade({
            "side": "LONG", "entry_price": 50000.0, "exit_price": 51000.0,
            "quantity": 0.0001, "pnl": 1.0, "reason": "TP",
        })
        reset_database(initial_balance=8.0)

        assert fetch_logs(limit=10) == []
        assert fetch_trades(limit=10) == []

    def test_reset_reinitialise_wallet(self, fresh_db):
        save_wallet_state(8.0, 3.0, 0.001, 50000.0)
        reset_database(initial_balance=10.0)

        state = get_wallet_state()
        assert state["cash"] == 10.0
        assert state["position_qty"] == 0.0
        assert state["entry_price"] is None