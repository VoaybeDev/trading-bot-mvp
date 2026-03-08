import asyncio
from collections import deque

from .db import fetch_logs, fetch_trades, init_db, insert_log, reset_database
from .market_data import MarketDataError, get_latest_price, get_recent_closes
from .paper_wallet import PaperWallet
from .settings import get_settings, init_settings
from .strategy import analyze

# Nombre de tentatives max lors d'une erreur réseau Binance
MAX_RETRY = 3
# Délai en secondes entre chaque retry
RETRY_DELAY = 2.0
# Délai entre chaque tick du run_loop (secondes)
TICK_INTERVAL = 5.0


class TradingBot:
    def __init__(self):
        init_settings()
        self._load_settings()
        init_db(initial_balance=self.initial_balance)

        self.running = False
        self.wallet = PaperWallet(initial_balance=self.initial_balance)
        self.prices = deque(maxlen=100)
        self.current_price = 0.0

        # Compteur d'erreurs réseau consécutives
        self._consecutive_errors = 0
        # Nombre max d'erreurs consécutives avant d'arrêter le bot
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
        """
        Rafraîchit les données de marché depuis Binance.
        Réessaie jusqu'à MAX_RETRY fois en cas d'erreur réseau.
        Lève MarketDataError si toutes les tentatives échouent.
        """
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

                # Succès — réinitialise le compteur d'erreurs
                self._consecutive_errors = 0
                return

            except MarketDataError as exc:
                last_exc = exc
                if attempt < MAX_RETRY:
                    self._log(
                        f"Erreur réseau Binance (tentative {attempt}/{MAX_RETRY}): {exc} "
                        f"— nouvelle tentative dans {RETRY_DELAY}s"
                    )
                    # Pause synchrone entre les retries
                    import time
                    time.sleep(RETRY_DELAY)

            except Exception as exc:
                # Erreur inattendue (JSON malformé, timeout SSL, etc.)
                last_exc = MarketDataError(f"Erreur inattendue: {exc}")
                self._log(f"Erreur inattendue lors du refresh marché: {exc}")
                break

        # Toutes les tentatives ont échoué
        self._consecutive_errors += 1
        self._log(
            f"Echec après {MAX_RETRY} tentatives. "
            f"Erreurs consécutives: {self._consecutive_errors}/{self._max_consecutive_errors}"
        )
        raise last_exc

    def _seed_prices(self):
        """Initialisation au démarrage — ne bloque pas si le réseau est indisponible."""
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
        """
        Exécute un cycle complet : refresh marché + logique de trading.
        Arrête le bot automatiquement si trop d'erreurs consécutives.
        """
        try:
            self._refresh_market()
        except MarketDataError as exc:
            self._log(f"Erreur marché pendant tick: {exc}")

            # Arrêt automatique si trop d'erreurs réseau d'affilée
            if self._consecutive_errors >= self._max_consecutive_errors:
                self.running = False
                self._log(
                    f"Bot arrêté automatiquement après {self._max_consecutive_errors} "
                    f"erreurs réseau consécutives. Vérifiez votre connexion ou l'API Binance."
                )
            return

        self._log(
            f"Tick | price={self.current_price} | signal={self.last_signal['signal']} | "
            f"score={self.last_signal['score']} | strong={self.last_signal['strong']}"
        )

        # ── Gestion position ouverte ──────────────────────────────────────
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
                return

            if pnl <= self.stop_loss_usd:
                trade = self.wallet.close_long(
                    self.current_price, f"SL {self.stop_loss_usd}$"
                )
                self.running = False
                self._log(f"Trade perdant fermé, bot stoppé: {trade}")
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
        else:
            self._log("Aucune entrée: attente d'un BUY fort")

    # ─── RUN LOOP ────────────────────────────────────────────────────────────

    async def run_loop(self):
        """
        Boucle principale asynchrone.
        Gère les exceptions inattendues pour ne jamais crasher silencieusement.
        """
        self._log("Boucle de trading démarrée")
        while self.running:
            try:
                self.tick()
            except Exception as exc:
                # Capture toute exception non prévue pour éviter un crash silencieux
                self._log(f"Erreur critique inattendue dans run_loop: {exc}")
                self._consecutive_errors += 1
                if self._consecutive_errors >= self._max_consecutive_errors:
                    self.running = False
                    self._log(
                        "Bot arrêté suite à des erreurs critiques répétées. "
                        "Consultez les logs pour diagnostiquer."
                    )
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
            # Infos de santé réseau exposées au frontend
            "health": {
                "consecutive_errors": self._consecutive_errors,
                "max_consecutive_errors": self._max_consecutive_errors,
            },
        }