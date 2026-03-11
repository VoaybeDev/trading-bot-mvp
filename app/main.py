import asyncio
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.params import Depends
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel

from .bot import TradingBot
from .db import fetch_logs, fetch_trades
from .health import build_health_report
from .settings import get_settings, reset_settings, update_settings
from .notifier import notify_bot_started, notify_bot_stopped

from datetime import datetime, timedelta
from .backtest import fetch_klines, run_backtest

# ─── CONFIG ─────────────────────────────────────────────────────────────────
API_KEY_VALUE = os.environ.get("API_KEY", "")
API_KEY_NAME  = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def verify_api_key(key: str = Security(api_key_header)) -> bool:
    if not API_KEY_VALUE:
        return True
    if key != API_KEY_VALUE:
        raise HTTPException(status_code=403, detail="Cle API invalide ou manquante")
    return True

# ─── APP ────────────────────────────────────────────────────────────────────
app = FastAPI(title="Trading Bot MVP - Real Market Data")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    if not API_KEY_VALUE:
        print("\n⚠️  AVERTISSEMENT : Variable d'environnement API_KEY non definie.")
        print("   Le serveur tourne en mode DEV sans authentification.")
        print("   Ajoutez API_KEY=votre_cle_secrete dans votre fichier .env\n")

bot = TradingBot()

# ─── SCHEMAS ────────────────────────────────────────────────────────────────
class SettingsUpdatePayload(BaseModel):
    symbol:           Optional[str]   = None
    interval:         Optional[str]   = None
    take_profit_usd:  Optional[float] = None
    stop_loss_usd:    Optional[float] = None
    initial_balance:  Optional[float] = None

class BacktestRequest(BaseModel):
    symbol:          str   = "BTCUSDT"
    interval:        str   = "1m"
    start:           str   = ""
    end:             str   = ""
    initial_balance: float = 8.0
    take_profit_usd: float = 1.0
    stop_loss_usd:   float = -1.0

# ─── ROUTES PUBLIQUES ───────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "Trading Bot MVP actif"}

# ─── ROUTES PROTEGEES ───────────────────────────────────────────────────────
@app.get("/status")
def status(auth: bool = Security(verify_api_key)):
    return bot.snapshot()

@app.get("/health")
def api_health(auth: bool = Security(verify_api_key)):
    return build_health_report(bot)

@app.post("/start")
async def start(auth: bool = Security(verify_api_key)):
    if not bot.running:
        bot.running = True
        bot._log("Bot demarre")
        asyncio.create_task(bot.run_loop())
        await notify_bot_started(bot.symbol, bot.interval)
    else:
        bot._log("Start ignore: bot deja en marche")
    return bot.snapshot()

@app.post("/stop")
async def stop(auth: bool = Security(verify_api_key)):
    bot.running = False
    bot._log("Bot arrete manuellement")
    await notify_bot_stopped("Manuel")
    return bot.snapshot()

@app.post("/tick")
def tick(auth: bool = Security(verify_api_key)):
    bot.tick()
    return bot.snapshot()

@app.get("/trades")
def trades(auth: bool = Security(verify_api_key)):
    return fetch_trades(limit=100)

@app.get("/logs")
def logs(auth: bool = Security(verify_api_key)):
    return fetch_logs(limit=100)

@app.post("/reset")
def reset(auth: bool = Security(verify_api_key)):
    bot.reset()
    return bot.snapshot()

@app.get("/settings")
def read_settings(auth: bool = Security(verify_api_key)):
    return get_settings()

@app.post("/settings/update")
def api_update_settings(
    payload: SettingsUpdatePayload,
    auth: bool = Security(verify_api_key),
):
    try:
        updated = update_settings(**payload.model_dump(exclude_none=True))
        bot.reset()
        bot._log(f"Parametres mis a jour: {updated}")
        return {
            "message": "Parametres mis a jour et bot reinitialise",
            "settings": updated,
            "status": bot.snapshot(),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/settings/reset")
def api_reset_settings(auth: bool = Security(verify_api_key)):
    settings = reset_settings()
    bot.reset()
    bot._log("Parametres reinitialises aux valeurs par defaut")
    return {
        "message": "Parametres reinitialises",
        "settings": settings,
        "status": bot.snapshot(),
    }

@app.post("/backtest")
async def backtest(req: BacktestRequest, _: bool = Security(verify_api_key)):
    """Lance un backtest sur les données historiques Binance."""
    if req.end:
        end_dt = datetime.fromisoformat(req.end)
    else:
        end_dt = datetime.utcnow()

    if req.start:
        start_dt = datetime.fromisoformat(req.start)
    else:
        start_dt = end_dt - timedelta(days=7)

    klines = await fetch_klines(req.symbol, req.interval, start_dt, end_dt)
    result = run_backtest(
        klines,
        initial_balance=req.initial_balance,
        take_profit_usd=req.take_profit_usd,
        stop_loss_usd=req.stop_loss_usd,
    )
    return result