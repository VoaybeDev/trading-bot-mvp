"""
notifier.py — Notifications Telegram pour NexTrade.
Placez ce fichier dans : trading-bot-mvp/app/notifier.py

Variables d'environnement requises :
    TELEGRAM_TOKEN   — Token du bot Telegram (via @BotFather)
    TELEGRAM_CHAT_ID — ID du chat/channel destinataire

Si les variables sont absentes, les notifications sont silencieusement ignorées.
"""
from __future__ import annotations

import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN",   "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

TELEGRAM_API = "https://api.telegram.org"


# ─── CORE ─────────────────────────────────────────────────────────────────────

def _is_configured() -> bool:
    return bool(TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)


async def send_message(text: str, token: Optional[str] = None, chat_id: Optional[str] = None) -> bool:
    """
    Envoie un message Telegram.
    Retourne True si succès, False sinon.
    Les erreurs sont loggées mais ne lèvent jamais d'exception.
    """
    t = token   or TELEGRAM_TOKEN
    c = chat_id or TELEGRAM_CHAT_ID

    if not t or not c:
        logger.debug("Telegram non configuré — notification ignorée.")
        return False

    url = f"{TELEGRAM_API}/bot{t}/sendMessage"
    payload = {
        "chat_id":    c,
        "text":       text,
        "parse_mode": "HTML",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return True
    except Exception as exc:
        logger.warning("Échec notification Telegram : %s", exc)
        return False


# ─── ÉVÉNEMENTS ───────────────────────────────────────────────────────────────

async def notify_bot_started(symbol: str, interval: str) -> bool:
    text = (
        "🟢 <b>NexTrade — Bot démarré</b>\n"
        f"📊 Symbol   : <code>{symbol}</code>\n"
        f"⏱  Interval : <code>{interval}</code>"
    )
    return await send_message(text)


async def notify_bot_stopped(reason: str = "Manuel") -> bool:
    text = (
        "🔴 <b>NexTrade — Bot arrêté</b>\n"
        f"📋 Raison : <code>{reason}</code>"
    )
    return await send_message(text)


async def notify_buy(symbol: str, price: float, qty: float, score: int) -> bool:
    text = (
        "📈 <b>NexTrade — Signal BUY exécuté</b>\n"
        f"💱 Symbol : <code>{symbol}</code>\n"
        f"💰 Prix   : <code>{price} $</code>\n"
        f"📦 Qté    : <code>{qty:.6f}</code>\n"
        f"🎯 Score  : <code>{score}%</code>"
    )
    return await send_message(text)


async def notify_sell(symbol: str, price: float, pnl: float, reason: str) -> bool:
    emoji = "✅" if pnl >= 0 else "❌"
    pnl_str = f"+{pnl:.4f}" if pnl >= 0 else f"{pnl:.4f}"
    text = (
        f"{emoji} <b>NexTrade — Signal SELL ({reason})</b>\n"
        f"💱 Symbol : <code>{symbol}</code>\n"
        f"💰 Prix   : <code>{price} $</code>\n"
        f"📊 PnL    : <code>{pnl_str} $</code>"
    )
    return await send_message(text)


async def notify_take_profit(symbol: str, price: float, pnl: float) -> bool:
    text = (
        "🎯 <b>NexTrade — Take Profit atteint !</b>\n"
        f"💱 Symbol : <code>{symbol}</code>\n"
        f"💰 Prix   : <code>{price} $</code>\n"
        f"✅ PnL    : <code>+{pnl:.4f} $</code>"
    )
    return await send_message(text)


async def notify_stop_loss(symbol: str, price: float, pnl: float) -> bool:
    text = (
        "🛑 <b>NexTrade — Stop Loss déclenché</b>\n"
        f"💱 Symbol : <code>{symbol}</code>\n"
        f"💰 Prix   : <code>{price} $</code>\n"
        f"❌ PnL    : <code>{pnl:.4f} $</code>"
    )
    return await send_message(text)


async def notify_error(message: str, consecutive_errors: int = 0) -> bool:
    text = (
        "⚠️ <b>NexTrade — Erreur réseau</b>\n"
        f"📋 Message : <code>{message}</code>\n"
        f"🔢 Erreurs consécutives : <code>{consecutive_errors}</code>"
    )
    return await send_message(text)


async def notify_bot_auto_stopped(consecutive_errors: int) -> bool:
    text = (
        "🚨 <b>NexTrade — Bot arrêté automatiquement</b>\n"
        f"🔢 Trop d'erreurs consécutives : <code>{consecutive_errors}</code>\n"
        "👉 Vérifiez la connexion et redémarrez le bot."
    )
    return await send_message(text)