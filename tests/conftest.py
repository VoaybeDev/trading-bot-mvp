"""
conftest.py — Fixtures partagées entre tous les tests.
Placez ce fichier dans : trading-bot-mvp/tests/conftest.py
"""
import pytest

MOCK_SETTINGS = {
    "symbol":          "BTCUSDT",
    "interval":        "1m",
    "take_profit_usd": 1.0,
    "stop_loss_usd":   -1.0,
    "initial_balance": 8.0,
}


@pytest.fixture(autouse=True)
def use_temp_db(monkeypatch, tmp_path):
    """
    Chaque test utilise une base SQLite isolee.
    - Patch DB_PATH dans db.py
    - Mock toutes les fonctions settings (settings.py a sa propre DB)
    """
    temp_db = tmp_path / "test_trading_bot.db"

    import app.db as db_module
    monkeypatch.setattr(db_module, "DB_PATH", temp_db)

    import app.settings as settings_module
    monkeypatch.setattr(settings_module, "get_settings",    lambda: MOCK_SETTINGS.copy())
    monkeypatch.setattr(settings_module, "init_settings",   lambda: None)
    monkeypatch.setattr(settings_module, "update_settings", lambda **kwargs: {**MOCK_SETTINGS, **kwargs})
    monkeypatch.setattr(settings_module, "reset_settings",  lambda: MOCK_SETTINGS.copy())

    yield temp_db


@pytest.fixture
def fresh_db(use_temp_db):
    """Base de donnees initialisee et vide."""
    from app.db import init_db
    init_db(initial_balance=8.0)
    return use_temp_db


@pytest.fixture
def wallet(fresh_db):
    """PaperWallet avec 8$ de capital initial."""
    from app.paper_wallet import PaperWallet
    return PaperWallet(initial_balance=8.0)


@pytest.fixture
def mock_market(monkeypatch):
    """Remplace les appels reseau Binance par des valeurs fixes."""
    import app.market_data as md
    monkeypatch.setattr(md, "get_latest_price",
                        lambda symbol: 50000.0)
    monkeypatch.setattr(md, "get_recent_closes",
                        lambda symbol, interval, limit: [50000.0 - i * 10 for i in range(limit)])
    return {"price": 50000.0, "closes": [50000.0 - i * 10 for i in range(30)]}


@pytest.fixture
def bot(fresh_db, mock_market):
    """TradingBot complet avec marche mocke et DB isolee."""
    from app.bot import TradingBot
    return TradingBot()