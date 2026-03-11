import asyncio
from collections import deque

from .db import fetch_logs, fetch_trades, init_db, insert_log, reset_database
from .exchange import BinanceClient, BinanceExchangeError
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

MAX_RETRY   = 3
RETRY_DELAY = 2.0
TICK_INTERVAL = 5.0


class TradingBot:
    def __init__(self):
        init_settings()
        self._load_settings()
        init_db(initial_balance=self.initial_balance)

        self.running = False
        self.wallet  = PaperWallet(initial_balance=self.initial_balance)
        self.prices  = deque(maxlen=100)
        self.current_price = 0.0

        self._consecutive_errors    = 0
        self._max_consecutive_errors = 5

        self.last_signal = {
            "signal": "HOLD",
            "score":  0,
            "strong": False,
            "ma10":   None,
            "ma20":   None,
        }

        # ── État de la position réelle (mode real) ──────────────────────────
        self.real_position: dict = {
            "active":      False,
            "entry_price": 0.0,
            "qty":         0.0,
            "quote_spent": 0.0,
        }

        self._seed_prices()

    # ─── SETTINGS ────────────────────────────────────────────────────────────

    def _load_settings(self):
        s = get_settings()
        self.symbol          = s["symbol"]
        self.interval        = s["interval"]
        self.take_profit_usd = s["take_profit_usd"]
        self.stop_loss_usd   = s["stop_loss_usd"]
        self.initial_balance = s["initial_balance"]
        self.trading_mode    = s["trading_mode"]   # "paper" | "real"
        self.order_size_pct  = s["order_size_pct"] # 1–100
        self.use_testnet     = s["use_testnet"]    # bool

    def _log(self, message: str):
        insert_log(message)

    def _exchange(self) -> BinanceClient:
        return BinanceClient(use_testnet=self.use_testnet)

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
                self.last_signal   = analyze(list(self.prices))
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
                "signal": "HOLD", "score": 0,
                "strong": False, "ma10": None, "ma20": None,
            }
            self._log(f"Initialisation marché impossible: {exc}")

    # ─── TICK ASYNC ──────────────────────────────────────────────────────────

    async def tick(self):
        """
        Cycle complet : refresh marché + logique de trading.
        Async pour supporter les ordres Binance réels.
        """
        try:
            self._refresh_market()
        except MarketDataError as exc:
            self._log(f"Erreur marché pendant tick: {exc}")
            await notify_error(str(exc), self._consecutive_errors)
            if self._consecutive_errors >= self._max_consecutive_errors:
                self.running = False
                self._log(
                    f"Bot arrêté automatiquement après {self._max_consecutive_errors} "
                    f"erreurs réseau consécutives."
                )
                await notify_bot_auto_stopped(self._consecutive_errors)
            return

        self._log(
            f"Tick | price={self.current_price} | signal={self.last_signal['signal']} | "
            f"score={self.last_signal['score']} | strong={self.last_signal['strong']} | "
            f"mode={self.trading_mode}"
        )

        if self.trading_mode == "real":
            await self._tick_real()
        else:
            self._tick_paper()

    # ─── PAPER TRADING ───────────────────────────────────────────────────────

    def _tick_paper(self):
        """Logique de trading paper (wallet simulé)."""
        if self.wallet.has_position():
            pnl = self.wallet.position_pnl(self.current_price)
            self._log(
                f"Position ouverte | entry={self.wallet.entry_price:.4f} | "
                f"current={self.current_price:.4f} | pnl={pnl:.4f}"
            )

            if pnl >= self.take_profit_usd:
                self.wallet.close_long(self.current_price, f"TP {self.take_profit_usd}$")
                self._log(f"Take Profit atteint: pnl={pnl:.4f}$")
                asyncio.ensure_future(
                    notify_take_profit(self.symbol, self.current_price, pnl)
                )
                return

            if pnl <= self.stop_loss_usd:
                self.wallet.close_long(self.current_price, f"SL {self.stop_loss_usd}$")
                self.running = False
                self._log(f"Stop Loss déclenché: pnl={pnl:.4f}$")
                asyncio.ensure_future(
                    notify_stop_loss(self.symbol, self.current_price, pnl)
                )
                return

            self._log(
                f"Position conservée: attente TP {self.take_profit_usd}$ "
                f"ou SL {self.stop_loss_usd}$"
            )
            return

        if self.last_signal["signal"] == "BUY" and self.last_signal["strong"]:
            order = self.wallet.open_long(self.current_price)
            if order:
                self._log(f"Nouvelle position ouverte (paper): {order}")
                asyncio.ensure_future(
                    notify_buy(
                        symbol=self.symbol,
                        price=self.current_price,
                        qty=self.wallet.position_qty,
                        score=self.last_signal["score"],
                    )
                )
        else:
            self._log("Aucune entrée: attente d'un BUY fort")

    # ─── REAL TRADING ────────────────────────────────────────────────────────

    async def _tick_real(self):
        """Logique de trading réel via l'API Binance."""
        exchange = self._exchange()

        if not exchange.is_configured():
            self._log(
                "⚠️ Mode réel activé mais BINANCE_API_KEY / BINANCE_SECRET_KEY "
                "non configurées. Passage automatique en paper trading."
            )
            self._tick_paper()
            return

        # ── Position ouverte ─────────────────────────────────────────────────
        if self.real_position["active"]:
            entry  = self.real_position["entry_price"]
            qty    = self.real_position["qty"]
            pnl    = (self.current_price - entry) * qty

            self._log(
                f"[REAL] Position ouverte | entry={entry:.4f} | "
                f"current={self.current_price:.4f} | qty={qty:.6f} | pnl={pnl:.4f}"
            )

            should_close = False
            reason       = ""

            if pnl >= self.take_profit_usd:
                should_close = True
                reason       = f"TP {self.take_profit_usd}$"
            elif pnl <= self.stop_loss_usd:
                should_close = True
                reason       = f"SL {self.stop_loss_usd}$"

            if should_close:
                try:
                    order = await exchange.place_market_sell(self.symbol, qty)
                    avg_price = BinanceClient.parse_avg_price(order) or self.current_price
                    real_pnl  = (avg_price - entry) * qty

                    self._log(
                        f"[REAL] Position fermée ({reason}) | "
                        f"avg_sell={avg_price:.4f} | pnl_réel={real_pnl:.4f}$"
                    )
                    self.real_position = {
                        "active": False, "entry_price": 0.0,
                        "qty": 0.0, "quote_spent": 0.0,
                    }

                    if pnl >= self.take_profit_usd:
                        await notify_take_profit(self.symbol, avg_price, real_pnl)
                    else:
                        self.running = False
                        await notify_stop_loss(self.symbol, avg_price, real_pnl)

                except BinanceExchangeError as exc:
                    self._log(f"[REAL] Erreur lors de la vente: {exc}")
                    self._consecutive_errors += 1
                    await notify_error(str(exc), self._consecutive_errors)
                    if self._consecutive_errors >= self._max_consecutive_errors:
                        self.running = False
                        await notify_bot_auto_stopped(self._consecutive_errors)
            else:
                self._log(
                    f"[REAL] Position conservée: attente TP {self.take_profit_usd}$ "
                    f"ou SL {self.stop_loss_usd}$"
                )
            return

        # ── Recherche d'entrée ────────────────────────────────────────────────
        if self.last_signal["signal"] == "BUY" and self.last_signal["strong"]:
            try:
                usdt_balance = await exchange.get_usdt_balance()
                quote_amount = usdt_balance * (self.order_size_pct / 100.0)

                if quote_amount < 1.0:
                    self._log(
                        f"[REAL] Solde insuffisant: {usdt_balance:.2f} USDT "
                        f"(minimum 1 USDT requis)"
                    )
                    return

                order     = await exchange.place_market_buy(self.symbol, quote_amount)
                filled_qty = BinanceClient.parse_filled_qty(order)
                avg_price  = BinanceClient.parse_avg_price(order) or self.current_price

                self.real_position = {
                    "active":      True,
                    "entry_price": avg_price,
                    "qty":         filled_qty,
                    "quote_spent": quote_amount,
                }

                self._log(
                    f"[REAL] Position ouverte | avg_price={avg_price:.4f} | "
                    f"qty={filled_qty:.6f} | quote={quote_amount:.2f} USDT"
                )
                await notify_buy(
                    symbol=self.symbol,
                    price=avg_price,
                    qty=filled_qty,
                    score=self.last_signal["score"],
                )

            except BinanceExchangeError as exc:
                self._log(f"[REAL] Erreur lors de l'achat: {exc}")
                self._consecutive_errors += 1
                await notify_error(str(exc), self._consecutive_errors)
                if self._consecutive_errors >= self._max_consecutive_errors:
                    self.running = False
                    await notify_bot_auto_stopped(self._consecutive_errors)
        else:
            self._log("[REAL] Aucune entrée: attente d'un BUY fort")

    # ─── RUN LOOP ────────────────────────────────────────────────────────────

    async def run_loop(self):
        self._log("Boucle de trading démarrée")
        while self.running:
            try:
                await self.tick()
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
        self.real_position = {
            "active": False, "entry_price": 0.0,
            "qty": 0.0, "quote_spent": 0.0,
        }
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
                "symbol":        self.symbol,
                "interval":      self.interval,
                "current_price": self.current_price,
            },
            "settings": {
                "symbol":          self.symbol,
                "interval":        self.interval,
                "take_profit_usd": self.take_profit_usd,
                "stop_loss_usd":   self.stop_loss_usd,
                "initial_balance": self.initial_balance,
                "trading_mode":    self.trading_mode,
                "order_size_pct":  self.order_size_pct,
                "use_testnet":     self.use_testnet,
            },
            "last_signal":    self.last_signal,
            "wallet":         self.wallet.status(self.current_price),
            "real_position":  self.real_position,
            "trades":         fetch_trades(limit=20),
            "logs":           fetch_logs(limit=20),
            "health": {
                "consecutive_errors":     self._consecutive_errors,
                "max_consecutive_errors": self._max_consecutive_errors,
            },
        }