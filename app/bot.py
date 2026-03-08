import asyncio
import random
from collections import deque

from .db import fetch_logs, fetch_trades, init_db, insert_log, reset_database
from .paper_wallet import PaperWallet
from .strategy import analyze


class TradingBot:
    def __init__(self):
        self.initial_balance = 8.0
        init_db(initial_balance=self.initial_balance)

        self.running = False
        self.wallet = PaperWallet(initial_balance=self.initial_balance)
        self.prices = deque(maxlen=100)
        self.current_price = 100.0
        self.last_signal = {
            "signal": "HOLD",
            "score": 0,
            "strong": False,
            "ma10": None,
            "ma20": None,
        }

        self.take_profit_usd = 1.0
        self.stop_loss_usd = -1.0

        self._seed_prices()

    def _log(self, message):
        insert_log(message)

    def _simulate_next_price(self):
        move = random.uniform(-0.02, 0.02)
        next_price = self.current_price * (1 + move)
        return round(max(10.0, next_price), 4)

    def _seed_prices(self):
        self.prices.clear()
        self.current_price = 100.0

        for _ in range(30):
            self.current_price = self._simulate_next_price()
            self.prices.append(self.current_price)

        self.last_signal = analyze(list(self.prices))

    def tick(self):
        self.current_price = self._simulate_next_price()
        self.prices.append(self.current_price)
        self.last_signal = analyze(list(self.prices))

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
                trade = self.wallet.close_long(self.current_price, "TP +1$")
                self._log(f"Trade gagnant fermé: {trade}")
                return

            if pnl <= self.stop_loss_usd:
                trade = self.wallet.close_long(self.current_price, "SL -1$")
                self.running = False
                self._log(f"Trade perdant fermé, bot stoppé: {trade}")
                return

            self._log("Position conservée: attente TP +1$ ou SL -1$")
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
        reset_database(initial_balance=self.initial_balance)
        self.wallet = PaperWallet(initial_balance=self.initial_balance)
        self._seed_prices()
        self._log("Bot réinitialisé")

    def snapshot(self):
        return {
            "running": self.running,
            "current_price": self.current_price,
            "last_signal": self.last_signal,
            "wallet": self.wallet.status(self.current_price),
            "trades": fetch_trades(limit=20),
            "logs": fetch_logs(limit=20),
        }