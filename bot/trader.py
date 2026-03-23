"""Main trading loop: fetch data, generate signals, manage orders and risk."""

import logging
import time
from typing import Optional

import pandas as pd

from bot.order_manager import OrderManager
from bot.position_tracker import PositionTracker
from bot.risk_manager import RiskManager
from config.settings import Settings, DEFAULT_SETTINGS
from data.polymarket_client import PolymarketClient
from strategies.base_strategy import BaseStrategy, Position, Signal

logger = logging.getLogger(__name__)


class Trader:
    """Core trading loop that ties together strategy, risk, and order management."""

    def __init__(
        self,
        strategy: BaseStrategy,
        client: PolymarketClient,
        token_id: str,
        settings: Settings = DEFAULT_SETTINGS,
        account_name: str = "primary",
    ):
        self.strategy = strategy
        self.client = client
        self.token_id = token_id
        self.settings = settings
        self.account_name = account_name

        self.order_manager = OrderManager(client)
        self.position_tracker = PositionTracker()
        self.risk_manager = RiskManager(
            params=settings.risk,
            initial_capital=1000.0,
        )

        self._running = False

    def _fetch_latest_data(self) -> Optional[pd.DataFrame]:
        """Fetch the latest market data for the token.

        In a real implementation this would pull live order book / trade data
        from Polymarket and convert it to OHLCV-like candles. For now, this
        returns None as a placeholder that callers should override or extend.
        """
        # TODO: Implement live data feed from Polymarket or an aggregation service.
        logger.debug("Fetching latest data for token %s", self.token_id[:16])
        return None

    def _current_price(self, data: pd.DataFrame) -> float:
        """Extract the latest price from data."""
        return float(data["close"].iloc[-1])

    def _to_strategy_position(self) -> Optional[Position]:
        """Convert a TrackedPosition to the strategy's Position type."""
        tracked = self.position_tracker.get_position(self.token_id)
        if tracked is None:
            return None
        return Position(
            token_id=tracked.token_id,
            side=tracked.side,
            entry_price=tracked.entry_price,
            size=tracked.size,
            current_price=tracked.current_price,
        )

    def tick(self, data: pd.DataFrame) -> None:
        """Execute one cycle of the trading loop.

        This method is the heart of the bot. It can be called in a loop with
        live data, or invoked manually with historical data for testing.
        """
        if data is None or data.empty:
            return

        price = self._current_price(data)
        self.position_tracker.update_price(self.token_id, price)

        # Update equity for risk tracking
        equity = self.risk_manager.initial_capital + self.position_tracker.total_pnl
        self.risk_manager.update_equity(equity)

        open_positions = self.position_tracker.get_open_positions()
        strategy_pos = self._to_strategy_position()

        # --- Exit check ---
        if strategy_pos is not None:
            if self.strategy.should_exit(strategy_pos, data):
                logger.info("Exit signal for %s", self.token_id[:16])
                # Cancel open orders then close
                self.order_manager.cancel_existing_orders(token_id=self.token_id)

                exit_side = "SELL" if strategy_pos.side == "BUY" else "BUY"
                order_id = self.order_manager.place_limit_order(
                    token_id=self.token_id,
                    side=exit_side,
                    price=price,
                    size=strategy_pos.size,
                )
                if order_id:
                    trade = self.position_tracker.close_position(self.token_id, price)
                    if trade:
                        self.risk_manager.record_trade_pnl(trade.pnl)
                        logger.info("Trade closed: PnL=%.4f", trade.pnl)
                return

        # --- Entry check ---
        if not self.position_tracker.has_position(self.token_id):
            if not self.risk_manager.can_trade(open_positions):
                logger.debug("Risk manager blocked new trade")
                return

            signal = self.strategy.generate_signal(data)
            if signal == Signal.HOLD:
                return

            side = "BUY" if signal == Signal.BUY else "SELL"
            size = self.risk_manager.validate_order_size(price, self.settings.position_size)
            if size <= 0:
                return

            logger.info("Entry signal: %s %s @ %.4f x %.2f", side, self.token_id[:16], price, size)

            # Mandatory: cancel existing orders before placing new ones
            order_id = self.order_manager.place_order_with_cancel(
                token_id=self.token_id,
                side=side,
                price=price,
                size=size,
            )
            if order_id:
                self.position_tracker.open_position(
                    token_id=self.token_id,
                    side=side,
                    entry_price=price,
                    size=size,
                    account=self.account_name,
                )

    def run(self, token_id: Optional[str] = None) -> None:
        """Start the live trading loop.

        Args:
            token_id: Override the token to trade. If None, uses self.token_id.
        """
        if token_id:
            self.token_id = token_id

        self._running = True
        logger.info(
            "Starting trader: strategy=%s, token=%s, account=%s",
            self.strategy.name, self.token_id[:16], self.account_name,
        )

        while self._running:
            try:
                data = self._fetch_latest_data()
                if data is not None and not data.empty:
                    self.tick(data)
                else:
                    logger.debug("No data available, skipping tick")
            except Exception:
                logger.exception("Error in trading loop")

            time.sleep(self.settings.poll_interval_seconds)

    def stop(self) -> None:
        """Stop the trading loop."""
        self._running = False
        logger.info("Trader stopped")
