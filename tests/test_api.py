"""
test_api.py — Tests d'integration pour les endpoints FastAPI (app/main.py)
Placez ce fichier dans : trading-bot-mvp/tests/test_api.py
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


@pytest.fixture
def client_with_auth(fresh_db, mock_market, monkeypatch):
    monkeypatch.setenv("API_KEY", "test-secret-key-123")
    import importlib
    import app.main as main_module
    importlib.reload(main_module)
    from app.main import app
    return TestClient(app)


# ─── ROUTE PUBLIQUE ───────────────────────────────────────────────────────────

class TestRoutePublique:
    def test_root_retourne_200(self, client):
        assert client.get("/").status_code == 200
        assert "message" in client.get("/").json()


# ─── STATUS ───────────────────────────────────────────────────────────────────

class TestStatus:
    def test_status_retourne_200(self, client):
        assert client.get("/status").status_code == 200

    def test_status_contient_running(self, client):
        data = client.get("/status").json()
        assert "running" in data
        assert data["running"] is False

    def test_status_contient_market(self, client):
        data = client.get("/status").json()
        assert "market" in data
        assert data["market"]["symbol"] == "BTCUSDT"

    def test_status_contient_wallet(self, client):
        data = client.get("/status").json()
        assert "wallet" in data
        assert data["wallet"]["initial_balance"] == 8.0

    def test_status_contient_logs_et_trades(self, client):
        data = client.get("/status").json()
        assert "logs" in data and "trades" in data


# ─── START / STOP ─────────────────────────────────────────────────────────────

class TestStartStop:
    def test_start_retourne_200(self, client):
        assert client.post("/start").status_code == 200

    def test_stop_retourne_200(self, client):
        client.post("/start")
        assert client.post("/stop").status_code == 200

    def test_stop_arrete_le_bot(self, client):
        client.post("/start")
        client.post("/stop")
        assert client.get("/status").json()["running"] is False


# ─── TICK ─────────────────────────────────────────────────────────────────────

class TestTick:
    def test_tick_retourne_200(self, client):
        assert client.post("/tick").status_code == 200

    def test_tick_ajoute_un_log(self, client):
        client.post("/tick")
        assert len(client.get("/status").json()["logs"]) > 0


# ─── RESET ────────────────────────────────────────────────────────────────────

class TestReset:
    def test_reset_retourne_200(self, client):
        assert client.post("/reset").status_code == 200

    def test_reset_vide_les_trades(self, client):
        client.post("/tick")
        client.post("/reset")
        assert client.get("/status").json()["trades"] == []


# ─── SETTINGS ─────────────────────────────────────────────────────────────────

class TestSettings:
    def test_get_settings_retourne_200(self, client):
        assert client.get("/settings").status_code == 200

    def test_update_settings_retourne_200(self, client):
        response = client.post("/settings/update", json={
            "symbol": "ETHUSDT", "take_profit_usd": 2.0,
        })
        assert response.status_code == 200

    def test_update_settings_retourne_message(self, client):
        data = client.post("/settings/update", json={"symbol": "ETHUSDT"}).json()
        assert "message" in data

    def test_reset_settings_retourne_200(self, client):
        assert client.post("/settings/reset").status_code == 200


# ─── TRADES & LOGS ────────────────────────────────────────────────────────────

class TestTradesEtLogs:
    def test_get_trades_retourne_liste(self, client):
        assert isinstance(client.get("/trades").json(), list)

    def test_get_logs_retourne_liste(self, client):
        assert isinstance(client.get("/logs").json(), list)


# ─── AUTH ─────────────────────────────────────────────────────────────────────

class TestAuth:
    def test_sans_cle_retourne_403(self, client_with_auth):
        assert client_with_auth.get("/status").status_code == 403

    def test_cle_invalide_retourne_403(self, client_with_auth):
        response = client_with_auth.get("/status",
                                        headers={"X-API-Key": "mauvaise-cle"})
        assert response.status_code == 403

    def test_bonne_cle_retourne_200(self, client_with_auth):
        response = client_with_auth.get("/status",
                                        headers={"X-API-Key": "test-secret-key-123"})
        assert response.status_code == 200