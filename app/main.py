import asyncio
from fastapi import FastAPI

from .bot import TradingBot
from .db import fetch_logs, fetch_trades

app = FastAPI(title="Trading Bot MVP")
bot = TradingBot()


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