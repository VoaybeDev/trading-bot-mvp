import asyncio
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .bot import TradingBot
from .db import fetch_logs, fetch_trades
from .settings import get_settings, reset_settings, update_settings

app = FastAPI(title="Trading Bot MVP - Real Market Data")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bot = TradingBot()


class SettingsUpdatePayload(BaseModel):
    symbol: Optional[str] = None
    interval: Optional[str] = None
    take_profit_usd: Optional[float] = None
    stop_loss_usd: Optional[float] = None
    initial_balance: Optional[float] = None


@app.get("/")
def root():
    return {"message": "Trading Bot MVP actif"}


@app.get("/status")
def status():
    return bot.snapshot()


@app.post("/start")
async def start():
    if not bot.running:
        bot.running = True
        bot._log("Bot démarré")
        asyncio.create_task(bot.run_loop())
    else:
        bot._log("Start ignoré: bot déjà en marche")
    return bot.snapshot()


@app.post("/stop")
def stop():
    bot.running = False
    bot._log("Bot arrêté manuellement")
    return bot.snapshot()


@app.post("/tick")
def tick():
    bot.tick()
    return bot.snapshot()


@app.get("/trades")
def trades():
    return fetch_trades(limit=100)


@app.get("/logs")
def logs():
    return fetch_logs(limit=100)


@app.post("/reset")
def reset():
    bot.reset()
    return bot.snapshot()


@app.get("/settings")
def read_settings():
    return get_settings()


@app.post("/settings/update")
def api_update_settings(payload: SettingsUpdatePayload):
    try:
        updated = update_settings(**payload.model_dump(exclude_none=True))
        bot.reset()
        bot._log(f"Paramètres mis à jour: {updated}")
        return {
            "message": "Paramètres mis à jour et bot réinitialisé",
            "settings": updated,
            "status": bot.snapshot(),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/settings/reset")
def api_reset_settings():
    settings = reset_settings()
    bot.reset()
    bot._log("Paramètres réinitialisés aux valeurs par défaut")
    return {
        "message": "Paramètres réinitialisés",
        "settings": settings,
        "status": bot.snapshot(),
    }