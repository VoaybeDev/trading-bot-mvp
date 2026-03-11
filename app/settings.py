"""
settings.py — Paramètres configurables de NexTrade.
Fichier : trading-bot-mvp/app/settings.py

Stocke les paramètres dans la table `settings` de la base SQLite.
Utilise INSERT OR IGNORE pour la migration : les anciens enregistrements
sont préservés, les nouvelles clés sont ajoutées avec leur valeur par défaut.
"""
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "trading_bot.db")

# ─── VALEURS PAR DÉFAUT ───────────────────────────────────────────────────────
DEFAULTS: dict = {
    # Paramètres de trading
    "symbol":          "BTCUSDT",
    "interval":        "1m",
    "take_profit_usd": "1.0",
    "stop_loss_usd":   "-1.0",
    "initial_balance": "8.0",
    # Mode de trading
    "trading_mode":    "paper",   # "paper" | "real"
    "order_size_pct":  "100.0",   # % du capital à engager (1–100)
    "use_testnet":     "true",    # "true" | "false"
}

VALID_INTERVALS = {
    "1m", "3m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "12h", "1d",
}
VALID_MODES = {"paper", "real"}


# ─── CONNEXION ────────────────────────────────────────────────────────────────

def _conn():
    return sqlite3.connect(DB_PATH)


# ─── INIT ─────────────────────────────────────────────────────────────────────

def init_settings() -> None:
    """
    Crée la table settings si elle n'existe pas.
    Insère les valeurs par défaut sans écraser les valeurs existantes.
    Compatible avec les bases créées avant l'ajout des nouveaux champs.
    """
    with _conn() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        # INSERT OR IGNORE : préserve les valeurs existantes, ajoute les nouvelles
        for key, value in DEFAULTS.items():
            db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        db.commit()


# ─── LECTURE ──────────────────────────────────────────────────────────────────

def get_settings() -> dict:
    """Retourne tous les paramètres sous forme de dict typé."""
    with _conn() as db:
        rows = db.execute("SELECT key, value FROM settings").fetchall()

    raw = {k: v for k, v in rows}

    # Migration douce : complète les clés manquantes avec les defaults
    for key, default in DEFAULTS.items():
        if key not in raw:
            raw[key] = default

    return {
        "symbol":          raw["symbol"],
        "interval":        raw["interval"],
        "take_profit_usd": float(raw["take_profit_usd"]),
        "stop_loss_usd":   float(raw["stop_loss_usd"]),
        "initial_balance": float(raw["initial_balance"]),
        "trading_mode":    raw["trading_mode"],
        "order_size_pct":  float(raw["order_size_pct"]),
        "use_testnet":     raw["use_testnet"].lower() in ("true", "1", "yes"),
    }


# ─── MISE À JOUR ──────────────────────────────────────────────────────────────

def update_settings(**kwargs) -> dict:
    """
    Met à jour un ou plusieurs paramètres avec validation.
    Lève ValueError si une valeur est invalide.
    """
    if "symbol" in kwargs:
        if not str(kwargs["symbol"]).strip():
            raise ValueError("symbol ne peut pas être vide")

    if "interval" in kwargs:
        if kwargs["interval"] not in VALID_INTERVALS:
            raise ValueError(
                f"interval invalide. Valeurs acceptées : {sorted(VALID_INTERVALS)}"
            )

    if "take_profit_usd" in kwargs:
        if float(kwargs["take_profit_usd"]) <= 0:
            raise ValueError("take_profit_usd doit être positif")

    if "stop_loss_usd" in kwargs:
        if float(kwargs["stop_loss_usd"]) >= 0:
            raise ValueError("stop_loss_usd doit être négatif")

    if "initial_balance" in kwargs:
        if float(kwargs["initial_balance"]) <= 0:
            raise ValueError("initial_balance doit être positif")

    if "trading_mode" in kwargs:
        if kwargs["trading_mode"] not in VALID_MODES:
            raise ValueError(
                f"trading_mode invalide. Valeurs acceptées : {VALID_MODES}"
            )

    if "order_size_pct" in kwargs:
        pct = float(kwargs["order_size_pct"])
        if not (1.0 <= pct <= 100.0):
            raise ValueError("order_size_pct doit être entre 1 et 100")

    with _conn() as db:
        for key, value in kwargs.items():
            if key in DEFAULTS:
                db.execute(
                    "UPDATE settings SET value = ? WHERE key = ?",
                    (str(value), key),
                )
        db.commit()

    return get_settings()


# ─── RESET ────────────────────────────────────────────────────────────────────

def reset_settings() -> dict:
    """Remet tous les paramètres aux valeurs par défaut."""
    with _conn() as db:
        for key, value in DEFAULTS.items():
            db.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        db.commit()
    return get_settings()