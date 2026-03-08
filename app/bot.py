import asyncio
from collections import deque

from .db import fetch_logs, fetch_trades, init_db, insert_log, reset_database
from .market_data import MarketDataError, get_latest_price, get_recent_closes
from .paper_wallet import PaperWallet
from .settings import get_settings, init_settings
from .strategy import analyze


class TradingBot:
    def __init__(self):
        init_settings()
        self._load_settings()

        init_db(initial_balance=self.initial_balance)

        self.running = False
        self.wallet = PaperWallet(initial_balance=self.initial_balance)
        self.prices = deque(maxlen=100)
        self.current_price = 0.0
        self.last_signal = {
            "signal": "HOLD",
            "score": 0,
            "strong": False,
            "ma10": None,
            "ma20": None,
        }

        self._seed_prices()

    def _load_settings(self):
        settings = get_settings()
        self.symbol = settings["symbol"]
        self.interval = settings["interval"]
        self.take_profit_usd = settings["take_profit_usd"]
        self.stop_loss_usd = settings["stop_loss_usd"]
        self.initial_balance = settings["initial_balance"]

    def _log(self, message):
        insert_log(message)

    def _refresh_market(self):
        closes = get_recent_closes(
            symbol=self.symbol,
            interval=self.interval,
            limit=30,
        )
        latest_price = get_latest_price(symbol=self.symbol)

        self.prices.clear()
        self.prices.extend(closes)
        self.current_price = latest_price
        self.last_signal = analyze(list(self.prices))

    def _seed_prices(self):
        try:
            self._refresh_market()
            self._log(
                f"Marché initialisé | symbol={self.symbol} | interval={self.interval} | "
                f"price={self.current_price}"
            )
        except MarketDataError as exc:
            self.current_price = 0.0
            self.prices.clear()
            self.last_signal = {
                "signal": "HOLD",
                "score": 0,
                "strong": False,
                "ma10": None,
                "ma20": None,
            }
            self._log(f"Initialisation marché impossible: {exc}")

    def tick(self):
        try:
            self._refresh_market()
        except MarketDataError as exc:
            self._log(f"Erreur marché pendant tick: {exc}")
            return

        self._log(
            f"Tick | price={self.current_price} | signal={self.last_signal['signal']} | "
            f"score={self.last_signal['score']} | strong={self.last_signal['strong']}"
        )

        if self.wallet.has_position():
            pnl = self.wallet.position_pnl(self.current_price)

            self._log(
                f"Position ouverte | entry={self.wallet.entry_price:.4f} | "
                f"current={self.current_price:.4f} | pnl={pnl:.4f}"
            )

            if pnl >= self.take_profit_usd:
                trade = self.wallet.close_long(self.current_price, f"TP {self.take_profit_usd}$")
                self._log(f"Trade gagnant fermé: {trade}")
                return

            if pnl <= self.stop_loss_usd:
                trade = self.wallet.close_long(self.current_price, f"SL {self.stop_loss_usd}$")
                self.running = False
                self._log(f"Trade perdant fermé, bot stoppé: {trade}")
                return

            self._log(
                f"Position conservée: attente TP {self.take_profit_usd}$ "
                f"ou SL {self.stop_loss_usd}$"
            )
            return

        if self.last_signal["signal"] == "BUY" and self.last_signal["strong"]:
            order = self.wallet.open_long(self.current_price)
            if order:
                self._log(f"Nouvelle position ouverte: {order}")
        else:
            self._log("Aucune entrée: attente d'un BUY fort")

    async def run_loop(self):
        while self.running:
            self.tick()
            await asyncio.sleep(5)

    def reset(self):
        self.running = False
        self._load_settings()
        reset_database(initial_balance=self.initial_balance)
        self.wallet = PaperWallet(initial_balance=self.initial_balance)
        self._seed_prices()
        self._log("Bot réinitialisé avec les paramètres actuels")

    def snapshot(self):
        return {
            "running": self.running,
            "market": {
                "symbol": self.symbol,
                "interval": self.interval,
                "current_price": self.current_price,
            },
            "settings": {
                "symbol": self.symbol,
                "interval": self.interval,
                "take_profit_usd": self.take_profit_usd,
                "stop_loss_usd": self.stop_loss_usd,
                "initial_balance": self.initial_balance,
            },
            "last_signal": self.last_signal,
            "wallet": self.wallet.status(self.current_price),
            "trades": fetch_trades(limit=20),
            "logs": fetch_logs(limit=20),
        }