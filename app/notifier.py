"""
notifier.py — Notifications Telegram pour NexTrade.
Fichier : trading-bot-mvp/app/notifier.py

Deux modes de fonctionnement :
  1. RELAY (recommandé sur HF Spaces) :
     Définir NOTIFY_RELAY_URL + NOTIFY_SECRET dans les secrets HF.
     Le bot appelle le relay Vercel qui transmet à Telegram.
     → Contourne le blocage DNS de api.telegram.org sur HF Spaces.

  2. DIRECT (dev local) :
     Définir TELEGRAM_TOKEN + TELEGRAM_CHAT_ID dans .env local.
     Le bot appelle directement l'API Telegram.
"""
from __future__ import annotations

import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"

# ── Variables de module (patchables dans les tests) ──────────────────────────
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN",   "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ── Config relay Vercel ───────────────────────────────────────────────────────
# NOTIFY_RELAY_URL  = URL du relay Vercel
# NOTIFY_SECRET     = clé partagée entre HF et Vercel (header X-Notify-Secret)
NOTIFY_RELAY_URL = os.getenv("NOTIFY_RELAY_URL", "")
NOTIFY_SECRET    = os.getenv("NOTIFY_SECRET",    "")


# ─── CORE ─────────────────────────────────────────────────────────────────────

def _is_configured() -> bool:
    relay_ok  = bool(NOTIFY_RELAY_URL)
    direct_ok = bool(TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)
    return relay_ok or direct_ok


async def _send_via_relay(text: str) -> bool:
    headers = {"Content-Type": "application/json"}
    if NOTIFY_SECRET:
        headers["X-Notify-Secret"] = NOTIFY_SECRET

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                NOTIFY_RELAY_URL,
                json={"text": text},
                headers=headers,
            )
            resp.raise_for_status()
            return True
    except Exception as exc:
        logger.warning("Echec relay Vercel : %s", exc)
        return False


async def _send_direct(text: str, token: str, chat_id: str) -> bool:
    url     = f"{TELEGRAM_API}/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return True
    except Exception as exc:
        logger.warning("Echec notification Telegram directe : %s", exc)
        return False


async def send_message(
    text: str,
    token: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> bool:
    # Mode relay (HF Spaces)
    if NOTIFY_RELAY_URL:
        return await _send_via_relay(text)

    # Mode direct (dev local)
    t = token   or TELEGRAM_TOKEN
    c = chat_id or TELEGRAM_CHAT_ID

    if not t or not c:
        logger.debug("Telegram non configure — notification ignoree.")
        return False

    return await _send_direct(text, t, c)


# ─── EVENEMENTS ───────────────────────────────────────────────────────────────

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
    emoji   = "✅" if pnl >= 0 else "❌"
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