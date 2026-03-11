"""
exchange.py — Client Binance pour NexTrade.
Fichier : trading-bot-mvp/app/exchange.py
"""
from __future__ import annotations

import hashlib
import hmac
import math
import os
import time
from typing import Optional

import httpx

TESTNET_BASE = "https://testnet.binance.vision/api"
REAL_BASE    = "https://api.binance.com/api"


class BinanceExchangeError(Exception):
    pass


class BinanceClient:
    def __init__(self, use_testnet: bool = True):
        self.base_url    = TESTNET_BASE if use_testnet else REAL_BASE
        self.use_testnet = use_testnet

    def is_configured(self) -> bool:
        return bool(
            os.getenv("BINANCE_API_KEY",    "") and
            os.getenv("BINANCE_SECRET_KEY", "")
        )

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _sign(self, params: dict) -> dict:
        params["timestamp"] = int(time.time() * 1000)
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        signature = hmac.new(
            os.getenv("BINANCE_SECRET_KEY", "").encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _headers(self) -> dict:
        return {"X-MBX-APIKEY": os.getenv("BINANCE_API_KEY", "")}

    # ── Account ───────────────────────────────────────────────────────────────

    async def get_account(self) -> dict:
        params = self._sign({})
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.base_url}/v3/account",
                params=params,
                headers=self._headers(),
            )
            if resp.status_code != 200:
                raise BinanceExchangeError(
                    f"get_account HTTP {resp.status_code}: {resp.text}"
                )
            return resp.json()

    async def get_usdt_balance(self) -> float:
        account = await self.get_account()
        for asset in account.get("balances", []):
            if asset["asset"] == "USDT":
                return float(asset["free"])
        return 0.0

    async def get_asset_balance(self, asset: str) -> float:
        account = await self.get_account()
        for a in account.get("balances", []):
            if a["asset"] == asset:
                return float(a["free"])
        return 0.0

    # ── Symbol info ───────────────────────────────────────────────────────────

    async def get_step_size(self, symbol: str) -> float:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.base_url}/v3/exchangeInfo",
                params={"symbol": symbol},
            )
            if resp.status_code != 200:
                return 0.00001
            data = resp.json()

        for s in data.get("symbols", []):
            if s["symbol"] == symbol:
                for f in s.get("filters", []):
                    if f["filterType"] == "LOT_SIZE":
                        return float(f["stepSize"])
        return 0.00001

    @staticmethod
    def round_step(quantity: float, step_size: float) -> float:
        if step_size <= 0:
            return quantity
        precision = max(0, int(round(-math.log10(step_size))))
        return math.floor(quantity * 10 ** precision) / 10 ** precision

    # ── Orders ────────────────────────────────────────────────────────────────

    async def place_market_buy(self, symbol: str, quote_amount: float) -> dict:
        params = self._sign({
            "symbol":        symbol,
            "side":          "BUY",
            "type":          "MARKET",
            "quoteOrderQty": round(quote_amount, 2),
        })
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{self.base_url}/v3/order",
                params=params,
                headers=self._headers(),
            )
            if resp.status_code != 200:
                raise BinanceExchangeError(
                    f"place_market_buy HTTP {resp.status_code}: {resp.text}"
                )
            return resp.json()

    async def place_market_sell(self, symbol: str, quantity: float) -> dict:
        step = await self.get_step_size(symbol)
        qty  = self.round_step(quantity, step)

        if qty <= 0:
            raise BinanceExchangeError(
                f"Quantité invalide après arrondi: {qty} (original={quantity}, step={step})"
            )

        params = self._sign({
            "symbol":   symbol,
            "side":     "SELL",
            "type":     "MARKET",
            "quantity": qty,
        })
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{self.base_url}/v3/order",
                params=params,
                headers=self._headers(),
            )
            if resp.status_code != 200:
                raise BinanceExchangeError(
                    f"place_market_sell HTTP {resp.status_code}: {resp.text}"
                )
            return resp.json()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def parse_filled_qty(order: dict) -> float:
        return float(order.get("executedQty", 0.0))

    @staticmethod
    def parse_avg_price(order: dict) -> float:
        """Calcule le prix moyen d'exécution — arrondi à 8 décimales pour éviter
        les erreurs de virgule flottante (ex: 62499.99999 au lieu de 62500.0)."""
        fills = order.get("fills", [])
        if not fills:
            return 0.0
        total_qty  = sum(float(f["qty"])                        for f in fills)
        total_cost = sum(float(f["qty"]) * float(f["price"])   for f in fills)
        if total_qty <= 0:
            return 0.0
        return round(total_cost / total_qty, 8)