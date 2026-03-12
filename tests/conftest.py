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
    "trading_mode":    "paper",   # valeur par défaut sûre
    "order_size_pct":  100.0,
    "use_testnet":     True,
}


@pytest.fixture(autouse=True)
def use_temp_db(monkeypatch, tmp_path):
    """
    Chaque test utilise une base SQLite isolée.
    - Patch DB_PATH dans db.py ET settings.py
    - Mock toutes les fonctions settings dans settings.py ET dans app.bot
      (car bot.py importe via `from .settings import ...`, créant des
      références locales que le patch du module source ne suffit pas à couvrir)
    """
    temp_db = tmp_path / "test_trading_bot.db"

    # ── Base de données ───────────────────────────────────────────────────────
    import app.db as db_module
    monkeypatch.setattr(db_module, "DB_PATH", str(temp_db))

    # Patch DB_PATH dans settings.py aussi (settings a sa propre connexion)
    import app.settings as settings_module
    monkeypatch.setattr(settings_module, "DB_PATH", str(temp_db))

    # ── Fonctions settings — patch sur le module source ───────────────────────
    monkeypatch.setattr(settings_module, "get_settings",    lambda: MOCK_SETTINGS.copy())
    monkeypatch.setattr(settings_module, "init_settings",   lambda: None)
    monkeypatch.setattr(settings_module, "update_settings", lambda **kwargs: {**MOCK_SETTINGS, **kwargs})
    monkeypatch.setattr(settings_module, "reset_settings",  lambda: MOCK_SETTINGS.copy())

    # ── Fonctions settings — patch sur les références importées dans app.bot ──
    # bot.py fait `from .settings import get_settings, init_settings`
    # ce qui crée des références locales indépendantes du module source
    import app.bot as bot_module
    monkeypatch.setattr(bot_module, "get_settings",  lambda: MOCK_SETTINGS.copy())
    monkeypatch.setattr(bot_module, "init_settings", lambda: None)

    yield temp_db


@pytest.fixture
def fresh_db(use_temp_db):
    """Base de données initialisée et vide."""
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
    """
    Remplace les appels réseau Binance par des valeurs fixes.
    Patch à la fois sur app.market_data (module source) ET sur les
    références locales dans app.bot (importées via `from .market_data import ...`).
    """
    import app.market_data as md
    import app.bot as bot_module

    price  = 50000.0
    closes = [50000.0 - i * 10 for i in range(30)]

    # Patch sur le module source
    monkeypatch.setattr(md, "get_latest_price",  lambda symbol: price)
    monkeypatch.setattr(md, "get_recent_closes",
                        lambda symbol, interval, limit: [50000.0 - i * 10 for i in range(limit)])

    # Patch sur les références importées dans bot.py
    monkeypatch.setattr(bot_module, "get_latest_price",  lambda symbol: price)
    monkeypatch.setattr(bot_module, "get_recent_closes",
                        lambda symbol, interval, limit: [50000.0 - i * 10 for i in range(limit)])

    return {"price": price, "closes": closes}


@pytest.fixture
def bot(fresh_db, mock_market):
    """TradingBot complet avec marché mocké et DB isolée."""
    from app.bot import TradingBot
    return TradingBot()