import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH  = BASE_DIR / "trading_bot.db"

# ─── LIMITES DE PURGE AUTOMATIQUE ────────────────────────────────────────────
# Au-delà de ces seuils, les anciennes entrées sont supprimées automatiquement
MAX_LOGS   = 500   # conserve les 500 logs les plus récents
MAX_TRADES = 200   # conserve les 200 trades les plus récents


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─── INIT ────────────────────────────────────────────────────────────────────

def init_db(initial_balance=8.0):
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS wallet_state (
            id              INTEGER PRIMARY KEY,
            initial_balance REAL    NOT NULL,
            cash            REAL    NOT NULL,
            position_qty    REAL    NOT NULL,
            entry_price     REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            side        TEXT    NOT NULL,
            entry_price REAL    NOT NULL,
            exit_price  REAL    NOT NULL,
            quantity    REAL    NOT NULL,
            pnl         REAL    NOT NULL,
            reason      TEXT    NOT NULL,
            created_at  TEXT    NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bot_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            message    TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # Index pour accélérer les requêtes triées par id DESC
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_id
        ON trades (id DESC)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_logs_id
        ON bot_logs (id DESC)
    """)

    row = cur.execute("SELECT id FROM wallet_state WHERE id = 1").fetchone()
    if row is None:
        cur.execute("""
            INSERT INTO wallet_state (id, initial_balance, cash, position_qty, entry_price)
            VALUES (1, ?, ?, 0.0, NULL)
        """, (initial_balance, initial_balance))

    conn.commit()
    conn.close()


def ensure_db(initial_balance=8.0):
    init_db(initial_balance=initial_balance)


# ─── PURGE AUTOMATIQUE ───────────────────────────────────────────────────────

def purge_old_logs(conn, keep=MAX_LOGS):
    """
    Supprime les logs les plus anciens si le total dépasse `keep`.
    Appelé automatiquement à chaque insert_log().
    """
    conn.execute("""
        DELETE FROM bot_logs
        WHERE id NOT IN (
            SELECT id FROM bot_logs
            ORDER BY id DESC
            LIMIT ?
        )
    """, (keep,))


def purge_old_trades(conn, keep=MAX_TRADES):
    """
    Supprime les trades les plus anciens si le total dépasse `keep`.
    Appelé automatiquement à chaque insert_trade().
    """
    conn.execute("""
        DELETE FROM trades
        WHERE id NOT IN (
            SELECT id FROM trades
            ORDER BY id DESC
            LIMIT ?
        )
    """, (keep,))


# ─── WALLET ──────────────────────────────────────────────────────────────────

def get_wallet_state():
    ensure_db()
    conn = get_connection()
    row  = conn.execute("""
        SELECT initial_balance, cash, position_qty, entry_price
        FROM wallet_state
        WHERE id = 1
    """).fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "initial_balance": float(row["initial_balance"]),
        "cash":            float(row["cash"]),
        "position_qty":    float(row["position_qty"]),
        "entry_price":     float(row["entry_price"]) if row["entry_price"] is not None else None,
    }


def save_wallet_state(initial_balance, cash, position_qty, entry_price):
    ensure_db(initial_balance=initial_balance)
    conn = get_connection()
    conn.execute("""
        UPDATE wallet_state
        SET initial_balance = ?, cash = ?, position_qty = ?, entry_price = ?
        WHERE id = 1
    """, (initial_balance, cash, position_qty, entry_price))
    conn.commit()
    conn.close()


# ─── TRADES ──────────────────────────────────────────────────────────────────

def insert_trade(trade):
    ensure_db()
    conn = get_connection()
    conn.execute("""
        INSERT INTO trades (side, entry_price, exit_price, quantity, pnl, reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        trade["side"],
        trade["entry_price"],
        trade["exit_price"],
        trade["quantity"],
        trade["pnl"],
        trade["reason"],
        now_iso(),
    ))
    # Purge automatique après chaque insertion
    purge_old_trades(conn)
    conn.commit()
    conn.close()


def fetch_trades(limit=20):
    ensure_db()
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, side, entry_price, exit_price, quantity, pnl, reason, created_at
        FROM trades
        ORDER BY id DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()

    return [
        {
            "id":          row["id"],
            "side":        row["side"],
            "entry_price": float(row["entry_price"]),
            "exit_price":  float(row["exit_price"]),
            "quantity":    float(row["quantity"]),
            "pnl":         float(row["pnl"]),
            "reason":      row["reason"],
            "created_at":  row["created_at"],
        }
        for row in rows
    ]


# ─── LOGS ────────────────────────────────────────────────────────────────────

def insert_log(message):
    ensure_db()
    conn = get_connection()
    conn.execute("""
        INSERT INTO bot_logs (message, created_at)
        VALUES (?, ?)
    """, (message, now_iso()))
    # Purge automatique après chaque insertion
    purge_old_logs(conn)
    conn.commit()
    conn.close()


def fetch_logs(limit=20):
    ensure_db()
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, message, created_at
        FROM bot_logs
        ORDER BY id DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()

    return [
        {
            "id":         row["id"],
            "message":    row["message"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


# ─── STATS ───────────────────────────────────────────────────────────────────

def get_db_stats():
    """Retourne des statistiques sur la taille de la base (utile pour le monitoring)."""
    ensure_db()
    conn = get_connection()
    nb_trades = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    nb_logs   = conn.execute("SELECT COUNT(*) FROM bot_logs").fetchone()[0]
    conn.close()
    return {
        "trades_count": nb_trades,
        "logs_count":   nb_logs,
        "max_trades":   MAX_TRADES,
        "max_logs":     MAX_LOGS,
    }


# ─── RESET ───────────────────────────────────────────────────────────────────

def reset_database(initial_balance=8.0):
    ensure_db(initial_balance=initial_balance)
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("DELETE FROM trades")
    cur.execute("DELETE FROM bot_logs")
    cur.execute("DELETE FROM wallet_state")
    cur.execute("""
        INSERT INTO wallet_state (id, initial_balance, cash, position_qty, entry_price)
        VALUES (1, ?, ?, 0.0, NULL)
    """, (initial_balance, initial_balance))

    conn.commit()
    conn.close()