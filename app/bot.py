import asyncio
from collections import deque

from .db import fetch_logs, fetch_trades, init_db, insert_log, reset_database
from .market_data import MarketDataError, get_latest_price, get_recent_closes
from .paper_wallet import PaperWallet
from .settings import get_settings, init_settings
from .strategy import analyze
from .notifier import (
    notify_buy,
    notify_sell,
    notify_take_profit,
    notify_stop_loss,
    notify_error,
    notify_bot_auto_stopped,
)

# Nombre de tentatives max lors d'une erreur réseau Binance
MAX_RETRY = 3
# Délai en secondes entre chaque retry
RETRY_DELAY = 2.0
# Délai entre chaque tick du run_loop (secondes)
TICK_INTERVAL = 5.0


def _fire(coro):
    """Lance une coroutine en fire-and-forget dans la boucle asyncio courante."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(coro)
        else:
            loop.run_until_complete(coro)
    except Exception:
        pass


class TradingBot:
    def __init__(self):
        init_settings()
        self._load_settings()
        init_db(initial_balance=self.initial_balance)

        self.running = False
        self.wallet = PaperWallet(initial_balance=self.initial_balance)
        self.prices = deque(maxlen=100)
        self.current_price = 0.0

        self._consecutive_errors = 0
        self._max_consecutive_errors = 5

        self.last_signal = {
            "signal": "HOLD",
            "score": 0,
            "strong": False,
            "ma10": None,
            "ma20": None,
        }

        self._seed_prices()

    # ─── SETTINGS ────────────────────────────────────────────────────────────

    def _load_settings(self):
        settings = get_settings()
        self.symbol          = settings["symbol"]
        self.interval        = settings["interval"]
        self.take_profit_usd = settings["take_profit_usd"]
        self.stop_loss_usd   = settings["stop_loss_usd"]
        self.initial_balance = settings["initial_balance"]

    def _log(self, message):
        insert_log(message)

    # ─── MARCHÉ AVEC RETRY ───────────────────────────────────────────────────

    def _refresh_market(self):
        last_exc = None

        for attempt in range(1, MAX_RETRY + 1):
            try:
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

                self._consecutive_errors = 0
                return

            except MarketDataError as exc:
                last_exc = exc
                if attempt < MAX_RETRY:
                    self._log(
                        f"Erreur réseau Binance (tentative {attempt}/{MAX_RETRY}): {exc} "
                        f"— nouvelle tentative dans {RETRY_DELAY}s"
                    )
                    import time
                    time.sleep(RETRY_DELAY)

            except Exception as exc:
                last_exc = MarketDataError(f"Erreur inattendue: {exc}")
                self._log(f"Erreur inattendue lors du refresh marché: {exc}")
                break

        self._consecutive_errors += 1
        self._log(
            f"Echec après {MAX_RETRY} tentatives. "
            f"Erreurs consécutives: {self._consecutive_errors}/{self._max_consecutive_errors}"
        )
        raise last_exc

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

    # ─── TICK ────────────────────────────────────────────────────────────────

    def tick(self):
        try:
            self._refresh_market()
        except MarketDataError as exc:
            self._log(f"Erreur marché pendant tick: {exc}")
            _fire(notify_error(str(exc), self._consecutive_errors))

            if self._consecutive_errors >= self._max_consecutive_errors:
                self.running = False
                self._log(
                    f"Bot arrêté automatiquement après {self._max_consecutive_errors} "
                    f"erreurs réseau consécutives."
                )
                _fire(notify_bot_auto_stopped(self._consecutive_errors))
            return

        self._log(
            f"Tick | price={self.current_price} | signal={self.last_signal['signal']} | "
            f"score={self.last_signal['score']} | strong={self.last_signal['strong']}"
        )

        # ── Position ouverte ──────────────────────────────────────────────
        if self.wallet.has_position():
            pnl = self.wallet.position_pnl(self.current_price)

            self._log(
                f"Position ouverte | entry={self.wallet.entry_price:.4f} | "
                f"current={self.current_price:.4f} | pnl={pnl:.4f}"
            )

            if pnl >= self.take_profit_usd:
                trade = self.wallet.close_long(
                    self.current_price, f"TP {self.take_profit_usd}$"
                )
                self._log(f"Trade gagnant fermé: {trade}")
                _fire(notify_take_profit(self.symbol, self.current_price, pnl))
                return

            if pnl <= self.stop_loss_usd:
                trade = self.wallet.close_long(
                    self.current_price, f"SL {self.stop_loss_usd}$"
                )
                self.running = False
                self._log(f"Trade perdant fermé, bot stoppé: {trade}")
                _fire(notify_stop_loss(self.symbol, self.current_price, pnl))
                return

            self._log(
                f"Position conservée: attente TP {self.take_profit_usd}$ "
                f"ou SL {self.stop_loss_usd}$"
            )
            return

        # ── Recherche d'entrée ────────────────────────────────────────────
        if self.last_signal["signal"] == "BUY" and self.last_signal["strong"]:
            order = self.wallet.open_long(self.current_price)
            if order:
                self._log(f"Nouvelle position ouverte: {order}")
                _fire(notify_buy(
                    symbol=self.symbol,
                    price=self.current_price,
                    qty=self.wallet.position_qty,
                    score=self.last_signal["score"],
                ))
        else:
            self._log("Aucune entrée: attente d'un BUY fort")

    # ─── RUN LOOP ────────────────────────────────────────────────────────────

    async def run_loop(self):
        self._log("Boucle de trading démarrée")
        while self.running:
            try:
                self.tick()
            except Exception as exc:
                self._log(f"Erreur critique inattendue dans run_loop: {exc}")
                self._consecutive_errors += 1
                await notify_error(str(exc), self._consecutive_errors)
                if self._consecutive_errors >= self._max_consecutive_errors:
                    self.running = False
                    self._log("Bot arrêté suite à des erreurs critiques répétées.")
                    await notify_bot_auto_stopped(self._consecutive_errors)
                    break

            await asyncio.sleep(TICK_INTERVAL)

        self._log("Boucle de trading terminée")

    # ─── RESET ───────────────────────────────────────────────────────────────

    def reset(self):
        self.running = False
        self._consecutive_errors = 0
        self._load_settings()
        reset_database(initial_balance=self.initial_balance)
        self.wallet = PaperWallet(initial_balance=self.initial_balance)
        self._seed_prices()
        self._log("Bot réinitialisé avec les paramètres actuels")

    # ─── SNAPSHOT ────────────────────────────────────────────────────────────

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
            "health": {
                "consecutive_errors": self._consecutive_errors,
                "max_consecutive_errors": self._max_consecutive_errors,
            },
        }