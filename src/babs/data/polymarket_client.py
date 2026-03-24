"""Polymarket CLOB API client wrapper."""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class OrderResult:
    success: bool
    order_id: Optional[str] = None
    error: Optional[str] = None


class PolymarketClient:
    """Thin wrapper around py-clob-client for Polymarket interactions."""

    def __init__(
        self,
        private_key: Optional[str] = None,
        funder_address: Optional[str] = None,
        host: str = "https://clob.polymarket.com",
        chain_id: int = 137,
        signature_type: int = 2,
    ):
        self.private_key = private_key or os.getenv("POLYMARKET_PRIVATE_KEY", "")
        self.funder_address = funder_address or os.getenv("POLYMARKET_FUNDER_ADDRESS", "")
        self.host = host
        self.chain_id = chain_id
        self.signature_type = signature_type
        self.client: Optional[ClobClient] = None

    def connect(self) -> None:
        """Initialize and authenticate the CLOB client."""
        if not self.private_key:
            raise ValueError("POLYMARKET_PRIVATE_KEY is required")

        self.client = ClobClient(
            self.host,
            key=self.private_key,
            chain_id=self.chain_id,
            signature_type=self.signature_type,
            funder=self.funder_address or None,
        )

        # Derive or set API credentials
        self.client.set_api_creds(self.client.create_or_derive_api_creds())
        logger.info("Connected to Polymarket CLOB at %s", self.host)

    def _ensure_connected(self) -> ClobClient:
        if self.client is None:
            raise RuntimeError("Client not connected. Call connect() first.")
        return self.client

    def place_limit_order(
        self,
        token_id: str,
        side: str,
        price: float,
        size: float,
    ) -> OrderResult:
        """Place a limit order on Polymarket.

        Args:
            token_id: The condition token ID for the market outcome.
            side: "BUY" or "SELL".
            price: Limit price (0.0 - 1.0 for binary markets).
            size: Order size in units.

        Returns:
            OrderResult with success status and order ID.
        """
        client = self._ensure_connected()
        side_const = BUY if side.upper() == "BUY" else SELL

        try:
            order_args = OrderArgs(
                price=price,
                size=size,
                side=side_const,
                token_id=token_id,
            )
            signed_order = client.create_order(order_args)
            response = client.post_order(signed_order, OrderType.GTC)

            order_id = response.get("orderID") if isinstance(response, dict) else None
            logger.info(
                "Placed %s limit order: token=%s price=%.4f size=%.2f order_id=%s",
                side, token_id[:16], price, size, order_id,
            )
            return OrderResult(success=True, order_id=order_id)

        except Exception as e:
            logger.error("Failed to place order: %s", e)
            return OrderResult(success=False, error=str(e))

    def cancel_all_orders(
        self,
        market_id: Optional[str] = None,
        token_id: Optional[str] = None,
    ) -> bool:
        """Cancel all open orders, optionally filtered by market or token.

        Args:
            market_id: If provided, cancel only orders for this market.
            token_id: If provided, cancel only orders for this token.

        Returns:
            True if cancellation succeeded.
        """
        client = self._ensure_connected()

        try:
            if token_id:
                client.cancel_all(asset_id=token_id)
            elif market_id:
                client.cancel_all(market=market_id)
            else:
                client.cancel_all()
            logger.info("Cancelled all open orders (market=%s, token=%s)", market_id, token_id)
            return True
        except Exception as e:
            logger.error("Failed to cancel orders: %s", e)
            return False

    def get_open_orders(self, market_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve all open orders."""
        client = self._ensure_connected()
        try:
            if market_id:
                orders = client.get_orders(market=market_id)
            else:
                orders = client.get_orders()
            return orders if isinstance(orders, list) else []
        except Exception as e:
            logger.error("Failed to fetch open orders: %s", e)
            return []

    def get_market_info(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """Fetch market information by condition ID."""
        client = self._ensure_connected()
        try:
            market = client.get_market(condition_id)
            return market if isinstance(market, dict) else None
        except Exception as e:
            logger.error("Failed to fetch market info: %s", e)
            return None

    def get_prices_history(
        self,
        token_id: str,
        interval: str = "5m",
        fidelity: int = 60,
    ) -> List[Dict[str, Any]]:
        """Fetch historical price data from the CLOB REST API.

        Args:
            token_id: The condition token ID.
            interval: Candle interval (e.g. "1m", "5m", "1h", "1d").
            fidelity: Number of data points to return.

        Returns:
            List of dicts with ``t`` (unix timestamp) and ``p`` (price) keys,
            ordered oldest-first.
        """
        url = f"{self.host}/prices-history"
        params = {
            "market": token_id,
            "interval": interval,
            "fidelity": fidelity,
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            history = resp.json()
            if isinstance(history, dict):
                history = history.get("history", [])
            if not isinstance(history, list):
                return []
            return history
        except Exception as e:
            logger.error("Failed to fetch prices history: %s", e)
            return []
