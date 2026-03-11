"""
#tests/test_health.py
test_health.py — Tests pour l'endpoint GET /health et le module app/health.py
Placez ce fichier dans : trading-bot-mvp/tests/test_health.py
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(fresh_db, mock_market, monkeypatch):
    monkeypatch.setenv("API_KEY", "")
    import importlib
    import app.main as main_module
    importlib.reload(main_module)
    from app.main import app
    return TestClient(app)


# ─── ENDPOINT /health ────────────────────────────────────────────────────────

class TestHealthEndpoint:

    def test_health_retourne_200(self, client):
        assert client.get("/health").status_code == 200

    def test_health_contient_toutes_les_cles(self, client):
        data = client.get("/health").json()
        assert "status"     in data
        assert "timestamp"  in data
        assert "version"    in data
        assert "components" in data

    def test_health_components_presents(self, client):
        components = client.get("/health").json()["components"]
        assert "database" in components
        assert "bot"      in components
        assert "wallet"   in components
        assert "market"   in components

    def test_health_status_ok_au_demarrage(self, client):
        data = client.get("/health").json()
        assert data["status"] == "ok"

    def test_health_timestamp_present(self, client):
        data = client.get("/health").json()
        # Format ISO : "2026-03-09T07:32:04"
        assert "T" in data["timestamp"]

    def test_health_version_presente(self, client):
        data = client.get("/health").json()
        assert data["version"] == "1.0.0"


# ─── COMPOSANT DATABASE ──────────────────────────────────────────────────────

class TestHealthDatabase:

    def test_db_status_ok(self, client):
        db = client.get("/health").json()["components"]["database"]
        assert db["status"] == "ok"

    def test_db_latency_presente(self, client):
        db = client.get("/health").json()["components"]["database"]
        assert "latency_ms" in db
        assert db["latency_ms"] >= 0

    def test_db_compteurs_presents(self, client):
        db = client.get("/health").json()["components"]["database"]
        assert "trades_count" in db
        assert "logs_count"   in db
        assert "max_trades"   in db
        assert "max_logs"     in db

    def test_db_compteurs_zero_au_demarrage(self, client):
        db = client.get("/health").json()["components"]["database"]
        assert db["trades_count"] == 0
        assert db["logs_count"]  >= 0

    def test_db_size_kb_present(self, client):
        db = client.get("/health").json()["components"]["database"]
        assert "size_kb" in db
        assert db["size_kb"] >= 0


# ─── COMPOSANT BOT ───────────────────────────────────────────────────────────

class TestHealthBot:

    def test_bot_status_stopped_au_demarrage(self, client):
        bot = client.get("/health").json()["components"]["bot"]
        assert bot["status"] == "stopped"

    def test_bot_status_running_apres_start(self, client):
        client.post("/start")
        bot = client.get("/health").json()["components"]["bot"]
        assert bot["status"] == "running"
        client.post("/stop")

    def test_bot_erreurs_zero_au_demarrage(self, client):
        bot = client.get("/health").json()["components"]["bot"]
        assert bot["consecutive_errors"] == 0

    def test_bot_error_rate_normal(self, client):
        bot = client.get("/health").json()["components"]["bot"]
        assert bot["error_rate"] == "normal"

    def test_bot_prix_present(self, client):
        bot = client.get("/health").json()["components"]["bot"]
        assert "current_price" in bot
        assert bot["current_price"] == 50000.0

    def test_bot_symbol_present(self, client):
        bot = client.get("/health").json()["components"]["bot"]
        assert bot["symbol"] == "BTCUSDT"


# ─── COMPOSANT WALLET ────────────────────────────────────────────────────────

class TestHealthWallet:

    def test_wallet_initial_balance(self, client):
        wallet = client.get("/health").json()["components"]["wallet"]
        assert wallet["initial_balance"] == 8.0

    def test_wallet_equity_egale_balance_sans_position(self, client):
        wallet = client.get("/health").json()["components"]["wallet"]
        assert wallet["equity"] == pytest.approx(8.0)

    def test_wallet_pnl_zero_au_demarrage(self, client):
        wallet = client.get("/health").json()["components"]["wallet"]
        assert wallet["daily_pnl_usd"] == pytest.approx(0.0, abs=1e-4)
        assert wallet["daily_pnl_pct"] == pytest.approx(0.0, abs=1e-4)

    def test_wallet_pas_de_position_au_demarrage(self, client):
        wallet = client.get("/health").json()["components"]["wallet"]
        assert wallet["has_position"] is False

    def test_wallet_cles_completes(self, client):
        wallet = client.get("/health").json()["components"]["wallet"]
        for key in ("initial_balance", "equity", "cash",
                    "has_position", "daily_pnl_usd", "daily_pnl_pct", "position_pnl"):
            assert key in wallet


# ─── COMPOSANT MARKET ────────────────────────────────────────────────────────

class TestHealthMarket:

    def test_market_symbol_present(self, client):
        market = client.get("/health").json()["components"]["market"]
        assert market["symbol"] == "BTCUSDT"

    def test_market_prix_present(self, client):
        market = client.get("/health").json()["components"]["market"]
        assert market["current_price"] == 50000.0

    def test_market_signal_present(self, client):
        market = client.get("/health").json()["components"]["market"]
        assert market["signal"] in ("BUY", "SELL", "HOLD")

    def test_market_cles_completes(self, client):
        market = client.get("/health").json()["components"]["market"]
        for key in ("symbol", "interval", "current_price",
                    "signal", "score", "strong", "ma10", "ma20"):
            assert key in market


# ─── STATUT GLOBAL DÉGRADÉ ───────────────────────────────────────────────────

class TestHealthStatusGlobal:

    def test_status_degrade_si_erreurs_reseau(self, client, monkeypatch):
        """Si le bot a >= 3 erreurs consécutives, le status passe à 'degraded'."""
        import app.main as main_module
        main_module.bot._consecutive_errors = 3
        data = client.get("/health").json()
        assert data["status"] == "degraded"
        # Reset
        main_module.bot._consecutive_errors = 0

    def test_status_ok_si_zero_erreurs(self, client):
        data = client.get("/health").json()
        assert data["status"] == "ok"