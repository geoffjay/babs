"""Order management: limit orders, cancellation, duplicate checking."""

import logging
from dataclasses import dataclass
from typing import Dict, Optional, Set

from babs.data.polymarket_client import PolymarketClient, OrderResult

logger = logging.getLogger(__name__)


@dataclass
class PendingOrder:
    order_id: str
    token_id: str
    side: str
    price: float
    size: float


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

    def cancel_existing_orders(
        self,
        market_id: Optional[str] = None,
        token_id: Optional[str] = None,
    ) -> bool:
        """Cancel all existing orders before placing new ones (mandatory step).

        Returns True if cancellation succeeded or there were no orders to cancel.
        """
        logger.info("Cancelling existing orders (market=%s, token=%s)", market_id, token_id)
        success = self.client.cancel_all_orders(market_id=market_id, token_id=token_id)
        if success:
            # Clear local tracking
            if token_id:
                self._pending_orders = {
                    oid: o for oid, o in self._pending_orders.items()
                    if o.token_id != token_id
                }
            else:
                self._pending_orders.clear()
            self._order_hashes.clear()
        return success

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
        exchange_ids = set()

        for order in open_orders:
            oid = order.get("id") or order.get("orderID", "")
            exchange_ids.add(oid)

        # Remove locally tracked orders that are no longer on the exchange
        stale = [oid for oid in self._pending_orders if oid not in exchange_ids]
        for oid in stale:
            removed = self._pending_orders.pop(oid)
            logger.info("Order %s no longer on exchange, removed from tracking", oid)

    def place_order_with_cancel(
        self,
        token_id: str,
        side: str,
        price: float,
        size: float,
    ) -> Optional[str]:
        """Convenience method: cancel existing orders then place a new one."""
        self.cancel_existing_orders(token_id=token_id)
        return self.place_limit_order(token_id, side, price, size)
