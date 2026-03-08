from .db import get_connection


DEFAULT_SETTINGS = {
    "symbol": "BTCUSDT",
    "interval": "1m",
    "take_profit_usd": 1.0,
    "stop_loss_usd": -1.0,
    "initial_balance": 8.0,
}


ALLOWED_INTERVALS = {
    "1m", "3m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "8h", "12h",
    "1d",
}


def init_settings():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bot_settings (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            interval TEXT NOT NULL,
            take_profit_usd REAL NOT NULL,
            stop_loss_usd REAL NOT NULL,
            initial_balance REAL NOT NULL
        )
    """)

    row = cur.execute("SELECT id FROM bot_settings WHERE id = 1").fetchone()

    if row is None:
        cur.execute("""
            INSERT INTO bot_settings (
                id,
                symbol,
                interval,
                take_profit_usd,
                stop_loss_usd,
                initial_balance
            )
            VALUES (1, ?, ?, ?, ?, ?)
        """, (
            DEFAULT_SETTINGS["symbol"],
            DEFAULT_SETTINGS["interval"],
            DEFAULT_SETTINGS["take_profit_usd"],
            DEFAULT_SETTINGS["stop_loss_usd"],
            DEFAULT_SETTINGS["initial_balance"],
        ))

    conn.commit()
    conn.close()


def _validate_symbol(symbol):
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("symbol doit être une chaîne non vide")
    return symbol.strip().upper()


def _validate_interval(interval):
    if not isinstance(interval, str) or interval not in ALLOWED_INTERVALS:
        raise ValueError(
            f"interval invalide. Valeurs autorisées: {sorted(ALLOWED_INTERVALS)}"
        )
    return interval


def _validate_take_profit_usd(value):
    value = float(value)
    if value <= 0:
        raise ValueError("take_profit_usd doit être > 0")
    return value


def _validate_stop_loss_usd(value):
    value = float(value)
    if value >= 0:
        raise ValueError("stop_loss_usd doit être < 0")
    return value


def _validate_initial_balance(value):
    value = float(value)
    if value <= 0:
        raise ValueError("initial_balance doit être > 0")
    return value


def get_settings():
    init_settings()

    conn = get_connection()
    row = conn.execute("""
        SELECT symbol, interval, take_profit_usd, stop_loss_usd, initial_balance
        FROM bot_settings
        WHERE id = 1
    """).fetchone()
    conn.close()

    if row is None:
        return DEFAULT_SETTINGS.copy()

    return {
        "symbol": row["symbol"],
        "interval": row["interval"],
        "take_profit_usd": float(row["take_profit_usd"]),
        "stop_loss_usd": float(row["stop_loss_usd"]),
        "initial_balance": float(row["initial_balance"]),
    }


def update_settings(
    symbol=None,
    interval=None,
    take_profit_usd=None,
    stop_loss_usd=None,
    initial_balance=None,
):
    init_settings()
    current = get_settings()

    if symbol is not None:
        current["symbol"] = _validate_symbol(symbol)

    if interval is not None:
        current["interval"] = _validate_interval(interval)

    if take_profit_usd is not None:
        current["take_profit_usd"] = _validate_take_profit_usd(take_profit_usd)

    if stop_loss_usd is not None:
        current["stop_loss_usd"] = _validate_stop_loss_usd(stop_loss_usd)

    if initial_balance is not None:
        current["initial_balance"] = _validate_initial_balance(initial_balance)

    conn = get_connection()
    conn.execute("""
        UPDATE bot_settings
        SET
            symbol = ?,
            interval = ?,
            take_profit_usd = ?,
            stop_loss_usd = ?,
            initial_balance = ?
        WHERE id = 1
    """, (
        current["symbol"],
        current["interval"],
        current["take_profit_usd"],
        current["stop_loss_usd"],
        current["initial_balance"],
    ))
    conn.commit()
    conn.close()

    return current


def reset_settings():
    init_settings()

    conn = get_connection()
    conn.execute("""
        UPDATE bot_settings
        SET
            symbol = ?,
            interval = ?,
            take_profit_usd = ?,
            stop_loss_usd = ?,
            initial_balance = ?
        WHERE id = 1
    """, (
        DEFAULT_SETTINGS["symbol"],
        DEFAULT_SETTINGS["interval"],
        DEFAULT_SETTINGS["take_profit_usd"],
        DEFAULT_SETTINGS["stop_loss_usd"],
        DEFAULT_SETTINGS["initial_balance"],
    ))
    conn.commit()
    conn.close()

    return get_settings()