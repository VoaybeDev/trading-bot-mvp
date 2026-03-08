from .db import get_wallet_state, insert_trade, save_wallet_state


class PaperWallet:
    """
    Portefeuille de simulation (paper trading).
    Toutes les opérations sont persistées en base SQLite via db.py.
    """

    def __init__(self, initial_balance=8.0):
        state = get_wallet_state()
        if state is None:
            self.initial_balance = initial_balance
            self.cash            = initial_balance
            self.position_qty    = 0.0
            self.entry_price     = None
            self._sync_state()
        else:
            self.initial_balance = state["initial_balance"]
            self.cash            = state["cash"]
            self.position_qty    = state["position_qty"]
            self.entry_price     = state["entry_price"]

    # ─── PERSISTANCE ─────────────────────────────────────────────────────────

    def _sync_state(self):
        """Sauvegarde l'état courant du wallet en base."""
        save_wallet_state(
            initial_balance=self.initial_balance,
            cash=self.cash,
            position_qty=self.position_qty,
            entry_price=self.entry_price,
        )

    # ─── ÉTAT ────────────────────────────────────────────────────────────────

    def has_position(self):
        """Retourne True si une position long est ouverte."""
        return self.position_qty > 0

    def equity(self, current_price):
        """Valeur totale du portefeuille au prix actuel."""
        if self.has_position():
            return self.position_qty * current_price
        return self.cash

    def position_pnl(self, current_price):
        """PnL non réalisé de la position ouverte (en USD)."""
        if not self.has_position():
            return 0.0
        return (current_price - self.entry_price) * self.position_qty

    def daily_pnl(self, current_price):
        """PnL depuis le début (equity actuelle - capital initial)."""
        return self.equity(current_price) - self.initial_balance

    # ─── ORDRES ──────────────────────────────────────────────────────────────

    def open_long(self, price):
        """
        Ouvre une position long en investissant tout le cash disponible.
        Retourne None si une position est déjà ouverte ou si le cash est vide.
        """
        if self.has_position() or self.cash <= 0:
            return None

        self.position_qty = self.cash / price
        self.entry_price  = price
        self.cash         = 0.0
        self._sync_state()

        return {
            "action":   "BUY",
            "price":    round(price, 4),
            "quantity": round(self.position_qty, 8),
        }

    def close_long(self, price, reason):
        """
        Ferme la position long au prix donné.
        Enregistre le trade en base. Retourne None si pas de position.
        """
        if not self.has_position():
            return None

        proceeds  = self.position_qty * price
        cost      = self.position_qty * self.entry_price
        pnl       = proceeds - cost

        trade = {
            "side":        "LONG",
            "entry_price": round(self.entry_price, 4),
            "exit_price":  round(price, 4),
            "quantity":    round(self.position_qty, 8),
            "pnl":         round(pnl, 4),
            "reason":      reason,
        }

        self.cash         = proceeds
        self.position_qty = 0.0
        self.entry_price  = None
        self._sync_state()
        insert_trade(trade)

        return trade

    # ─── SNAPSHOT ────────────────────────────────────────────────────────────

    def status(self, current_price):
        """Retourne un dict sérialisable de l'état du wallet."""
        return {
            "initial_balance": round(self.initial_balance, 4),
            "cash":            round(self.cash, 4),
            "has_position":    self.has_position(),
            "entry_price":     round(self.entry_price, 4) if self.entry_price is not None else None,
            "position_qty":    round(self.position_qty, 8),
            "equity":          round(self.equity(current_price), 4),
            "position_pnl":    round(self.position_pnl(current_price), 4),
            "daily_pnl":       round(self.daily_pnl(current_price), 4),
        }