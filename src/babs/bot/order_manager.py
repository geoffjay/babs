"""Order management: limit orders, cancellation, duplicate checking."""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Set

from babs.data.polymarket_client import PolymarketClient, OrderResult

logger = logging.getLogger(__name__)

# How many times to poll exchange after cancel before giving up
_CANCEL_VERIFY_RETRIES = 3
_CANCEL_VERIFY_DELAY = 0.5  # seconds between retries


class OrderState(Enum):
    PENDING = "pending"
    PLACED = "placed"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"


@dataclass
class PendingOrder:
    order_id: str
    token_id: str
    side: str
    price: float
    size: float
    state: OrderState = OrderState.PLACED


class OrderManager:
    """Manage limit orders on Polymarket with dedup and mandatory cancellation."""

    def __init__(self, client: PolymarketClient):
        self.client = client
        self._pending_orders: Dict[str, PendingOrder] = {}
        self._order_hashes: Set[str] = set()

    @staticmethod
    def _order_hash(token_id: str, side: str, price: float, size: float) -> str:
        """Create a dedup key for an order."""
        return f"{token_id}:{side}:{price:.6f}:{size:.4f}"

    def _verify_cancellation(self, token_id: Optional[str] = None) -> bool:
        """Poll the exchange to confirm no open orders remain for the token.

        Returns True if all orders for the token are confirmed cancelled.
        """
        for attempt in range(1, _CANCEL_VERIFY_RETRIES + 1):
            open_orders = self.client.get_open_orders()
            remaining = [
                o for o in open_orders
                if token_id is None
                or o.get("asset_id") == token_id
                or o.get("token_id") == token_id
            ]
            if not remaining:
                return True
            logger.debug(
                "Cancel verification attempt %d/%d: %d orders still open",
                attempt, _CANCEL_VERIFY_RETRIES, len(remaining),
            )
            if attempt < _CANCEL_VERIFY_RETRIES:
                time.sleep(_CANCEL_VERIFY_DELAY)

        logger.warning(
            "Cancel verification failed: %d orders still open after %d retries",
            len(remaining), _CANCEL_VERIFY_RETRIES,
        )
        return False

    def cancel_existing_orders(
        self,
        market_id: Optional[str] = None,
        token_id: Optional[str] = None,
        verify: bool = True,
    ) -> bool:
        """Cancel all existing orders before placing new ones (mandatory step).

        Args:
            market_id: If provided, cancel only orders for this market.
            token_id: If provided, cancel only orders for this token.
            verify: If True, poll the exchange to confirm cancellation propagated.

        Returns True if cancellation succeeded and was verified.
        """
        logger.info("Cancelling existing orders (market=%s, token=%s)", market_id, token_id)
        success = self.client.cancel_all_orders(market_id=market_id, token_id=token_id)
        if not success:
            return False

        # Mark local orders as cancelled
        if token_id:
            for oid, order in self._pending_orders.items():
                if order.token_id == token_id:
                    order.state = OrderState.CANCELLED
            self._pending_orders = {
                oid: o for oid, o in self._pending_orders.items()
                if o.token_id != token_id
            }
        else:
            for order in self._pending_orders.values():
                order.state = OrderState.CANCELLED
            self._pending_orders.clear()
        self._order_hashes.clear()

        if verify:
            return self._verify_cancellation(token_id=token_id)
        return True

    def place_limit_order(
        self,
        token_id: str,
        side: str,
        price: float,
        size: float,
    ) -> Optional[str]:
        """Place a limit order with duplicate checking.

        IMPORTANT: Always call cancel_existing_orders() before this method.

        Args:
            token_id: Condition token for the market outcome.
            side: "BUY" or "SELL".
            price: Limit price.
            size: Order size.

        Returns:
            Order ID if placed successfully, None otherwise.
        """
        # Duplicate check
        ohash = self._order_hash(token_id, side, price, size)
        if ohash in self._order_hashes:
            logger.warning("Duplicate order rejected: %s %s @ %.4f x %.2f", side, token_id[:16], price, size)
            return None

        result: OrderResult = self.client.place_limit_order(token_id, side, price, size)

        if result.success and result.order_id:
            self._pending_orders[result.order_id] = PendingOrder(
                order_id=result.order_id,
                token_id=token_id,
                side=side,
                price=price,
                size=size,
                state=OrderState.PLACED,
            )
            self._order_hashes.add(ohash)
            logger.info("Order placed: id=%s %s @ %.4f x %.2f", result.order_id, side, price, size)
            return result.order_id
        else:
            logger.error("Order failed: %s", result.error)
            return None

    def get_pending_orders(self) -> Dict[str, PendingOrder]:
        """Return locally tracked pending orders."""
        return dict(self._pending_orders)

    def sync_with_exchange(self) -> None:
        """Sync local order state with the exchange's open orders."""
        open_orders = self.client.get_open_orders()
        exchange_ids: Dict[str, dict] = {}

        for order in open_orders:
            oid = order.get("id") or order.get("orderID") or order.get("order_id", "")
            if oid:
                exchange_ids[oid] = order

        # Remove locally tracked orders that are no longer on the exchange
        # (they were filled or cancelled externally)
        stale = [oid for oid in self._pending_orders if oid not in exchange_ids]
        for oid in stale:
            removed = self._pending_orders.pop(oid)
            removed.state = OrderState.FILLED
            logger.info("Order %s no longer on exchange, removed from tracking", oid)

        # Update state for orders still on the exchange
        for oid, order in exchange_ids.items():
            if oid in self._pending_orders:
                size_matched = order.get("size_matched") or order.get("sizeMatched")
                if size_matched and float(size_matched) > 0:
                    self._pending_orders[oid].state = OrderState.PARTIAL

    def place_order_with_cancel(
        self,
        token_id: str,
        side: str,
        price: float,
        size: float,
    ) -> Optional[str]:
        """Cancel existing orders (with verification), then place a new one.

        If cancellation cannot be verified, the new order is NOT placed to
        prevent duplicate fills.
        """
        cancelled = self.cancel_existing_orders(token_id=token_id, verify=True)
        if not cancelled:
            logger.error(
                "Aborting order placement: could not verify cancellation for %s",
                token_id[:16],
            )
            return None
        return self.place_limit_order(token_id, side, price, size)
