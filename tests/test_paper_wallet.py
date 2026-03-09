"""
test_paper_wallet.py — Tests unitaires pour app/paper_wallet.py
Placez ce fichier dans : trading-bot-mvp/tests/test_paper_wallet.py
"""
import pytest
from app.paper_wallet import PaperWallet
from app.db import fetch_trades


# ─── INIT ─────────────────────────────────────────────────────────────────────

class TestPaperWalletInit:
    def test_capital_initial(self, wallet):
        assert wallet.initial_balance == 8.0
        assert wallet.cash == 8.0
        assert wallet.position_qty == 0.0
        assert wallet.entry_price is None

    def test_pas_de_position_au_depart(self, wallet):
        assert wallet.has_position() is False

    def test_persistance_au_rechargement(self, fresh_db):
        """Un wallet rechargé retrouve son état depuis la DB."""
        w1 = PaperWallet(initial_balance=8.0)
        w1.open_long(price=50000.0)

        # Nouveau wallet sur la même DB → doit retrouver la position
        w2 = PaperWallet(initial_balance=8.0)
        assert w2.has_position() is True
        assert w2.entry_price == 50000.0


# ─── EQUITY / PNL ─────────────────────────────────────────────────────────────

class TestEquityEtPnl:
    def test_equity_sans_position(self, wallet):
        assert wallet.equity(50000.0) == pytest.approx(8.0)

    def test_equity_avec_position(self, wallet):
        wallet.open_long(50000.0)
        qty = 8.0 / 50000.0
        assert wallet.equity(51000.0) == pytest.approx(qty * 51000.0)

    def test_position_pnl_zero_sans_position(self, wallet):
        assert wallet.position_pnl(50000.0) == 0.0

    def test_position_pnl_positif(self, wallet):
        wallet.open_long(50000.0)
        qty = 8.0 / 50000.0
        expected_pnl = (51000.0 - 50000.0) * qty
        assert wallet.position_pnl(51000.0) == pytest.approx(expected_pnl)

    def test_position_pnl_negatif(self, wallet):
        wallet.open_long(50000.0)
        assert wallet.position_pnl(49000.0) < 0

    def test_daily_pnl_zero_au_depart(self, wallet):
        assert wallet.daily_pnl(50000.0) == pytest.approx(0.0, abs=1e-6)

    def test_daily_pnl_apres_gain(self, wallet):
        wallet.open_long(50000.0)
        # Si le prix monte, le daily_pnl doit être positif
        assert wallet.daily_pnl(60000.0) > 0


# ─── OPEN LONG ────────────────────────────────────────────────────────────────

class TestOpenLong:
    def test_ouvre_position_correctement(self, wallet):
        order = wallet.open_long(50000.0)
        assert order is not None
        assert order["action"] == "BUY"
        assert order["price"] == 50000.0
        assert wallet.has_position() is True
        assert wallet.cash == 0.0
        assert wallet.entry_price == 50000.0

    def test_quantite_calculee_correctement(self, wallet):
        order = wallet.open_long(50000.0)
        expected_qty = 8.0 / 50000.0
        assert order["quantity"] == pytest.approx(expected_qty, rel=1e-6)

    def test_retourne_none_si_position_deja_ouverte(self, wallet):
        wallet.open_long(50000.0)
        result = wallet.open_long(51000.0)
        assert result is None

    def test_retourne_none_si_cash_zero(self, wallet):
        wallet.cash = 0.0
        wallet._sync_state()
        result = wallet.open_long(50000.0)
        assert result is None


# ─── CLOSE LONG ───────────────────────────────────────────────────────────────

class TestCloseLong:
    def test_ferme_position_correctement(self, wallet):
        wallet.open_long(50000.0)
        trade = wallet.close_long(51000.0, "TP 1$")

        assert trade is not None
        assert trade["side"] == "LONG"
        assert trade["entry_price"] == 50000.0
        assert trade["exit_price"] == 51000.0
        assert wallet.has_position() is False
        assert wallet.position_qty == 0.0
        assert wallet.entry_price is None

    def test_cash_mis_a_jour_apres_cloture(self, wallet):
        wallet.open_long(50000.0)
        qty = 8.0 / 50000.0
        wallet.close_long(51000.0, "TP")
        expected_cash = qty * 51000.0
        assert wallet.cash == pytest.approx(expected_cash)

    def test_pnl_positif_sur_gain(self, wallet):
        wallet.open_long(50000.0)
        trade = wallet.close_long(51000.0, "TP")
        assert trade["pnl"] > 0

    def test_pnl_negatif_sur_perte(self, wallet):
        wallet.open_long(50000.0)
        trade = wallet.close_long(49000.0, "SL")
        assert trade["pnl"] < 0

    def test_trade_enregistre_en_db(self, wallet):
        wallet.open_long(50000.0)
        wallet.close_long(51000.0, "TP 1$")
        trades = fetch_trades(limit=10)
        assert len(trades) == 1
        assert trades[0]["reason"] == "TP 1$"

    def test_retourne_none_sans_position(self, wallet):
        result = wallet.close_long(51000.0, "TP")
        assert result is None

    def test_raison_sauvegardee_correctement(self, wallet):
        wallet.open_long(50000.0)
        trade = wallet.close_long(51000.0, "SL -1$")
        assert trade["reason"] == "SL -1$"


# ─── STATUS ───────────────────────────────────────────────────────────────────

class TestStatus:
    def test_status_sans_position(self, wallet):
        status = wallet.status(50000.0)
        assert status["has_position"] is False
        assert status["entry_price"] is None
        assert status["cash"] == pytest.approx(8.0)
        assert status["equity"] == pytest.approx(8.0)
        assert status["daily_pnl"] == pytest.approx(0.0, abs=1e-4)

    def test_status_avec_position(self, wallet):
        wallet.open_long(50000.0)
        status = wallet.status(50000.0)
        assert status["has_position"] is True
        assert status["entry_price"] == 50000.0
        assert status["cash"] == 0.0

    def test_status_contient_toutes_les_cles(self, wallet):
        status = wallet.status(50000.0)
        expected_keys = {
            "initial_balance", "cash", "has_position",
            "entry_price", "position_qty", "equity",
            "position_pnl", "daily_pnl",
        }
        assert set(status.keys()) == expected_keys