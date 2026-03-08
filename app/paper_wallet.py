from .db import get_wallet_state, insert_trade, save_wallet_state


class PaperWallet:
    def __init__(self, initial_balance=8.0):
        state = get_wallet_state()

        if state is None:
            self.initial_balance = initial_balance
            self.cash = initial_balance
            self.position_qty = 0.0
            self.entry_price = None
            self._sync_state()
        else:
            self.initial_balance = state["initial_balance"]
            self.cash = state["cash"]
            self.position_qty = state["position_qty"]
            self.entry_price = state["entry_price"]

    def _sync_state(self):
        save_wallet_state(
            initial_balance=self.initial_balance,
            cash=self.cash,
            position_qty=self.position_qty,
            entry_price=self.entry_price,
        )

    def has_position(self):
        return self.position_qty > 0

    def equity(self, current_price):
        if self.has_position():
            return self.position_qty * current_price
        return self.cash

    def position_pnl(self, current_price):
        if not self.has_position():
            return 0.0
        return (current_price - self.entry_price) * self.position_qty

    def daily_pnl(self, current_price):
        return self.equity(current_price) - self.initial_balance

    def open_long(self, price):
        if self.has_position() or self.cash <= 0:
            return None

        self.position_qty = self.cash / price
        self.entry_price = price
        self.cash = 0.0
        self._sync_state()

        return {
            "action": "BUY",
            "price": round(price, 4),
            "quantity": round(self.position_qty, 8),
        }

    def close_long(self, price, reason):
        if not self.has_position():
            return None

        proceeds = self.position_qty * price
        cost = self.position_qty * self.entry_price
        pnl = proceeds - cost

        trade = {
            "side": "LONG",
            "entry_price": round(self.entry_price, 4),
            "exit_price": round(price, 4),
            "quantity": round(self.position_qty, 8),
            "pnl": round(pnl, 4),
            "reason": reason,
        }

        self.cash = proceeds
        self.position_qty = 0.0
        self.entry_price = None
        self._sync_state()
        insert_trade(trade)

        return trade

    def status(self, current_price):
        return {
            "initial_balance": round(self.initial_balance, 4),
            "cash": round(self.cash, 4),
            "has_position": self.has_position(),
            "entry_price": round(self.entry_price, 4) if self.entry_price is not None else None,
            "position_qty": round(self.position_qty, 8),
            "equity": round(self.equity(current_price), 4),
            "position_pnl": round(self.position_pnl(current_price), 4),
            "daily_pnl": round(self.daily_pnl(current_price), 4),
        }