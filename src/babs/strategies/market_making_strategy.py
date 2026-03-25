"""Market making strategy: captures bid-ask spread via inventory cycling."""

import numpy as np
import pandas as pd

from babs.strategies.base_strategy import BaseStrategy, Position, Signal


class MarketMakingStrategy(BaseStrategy):
    """Simulates two-sided market making by alternating buy/sell legs.

    Instead of predicting direction, this strategy profits from the bid-ask
    spread. It posts limit orders on one side, exits when the spread is
    captured, then posts on the other side. Spread width adapts to realized
    volatility and skews against accumulated inventory.
    """

    name = "mm"

    def __init__(
        self,
        base_spread: float = 0.02,
        volatility_lookback: int = 20,
        volatility_multiplier: float = 2.0,
        skew_factor: float = 0.5,
        max_inventory: float = 5.0,
        max_hold_bars: int = 10,
        inventory_stop_loss: float = 0.05,
        edge_buffer: float = 0.03,
        min_spread: float = 0.01,
    ):
        self.base_spread = base_spread
        self.volatility_lookback = volatility_lookback
        self.volatility_multiplier = volatility_multiplier
        self.skew_factor = skew_factor
        self.max_inventory = max_inventory
        self.max_hold_bars = max_hold_bars
        self.inventory_stop_loss = inventory_stop_loss
        self.edge_buffer = edge_buffer
        self.min_spread = min_spread

        self._inventory: float = 0.0
        self._bars_since_entry: int = 0
        self._last_spread: float = base_spread

    def required_history(self) -> int:
        return self.volatility_lookback + 5

    def _estimate_volatility(self, data: pd.DataFrame) -> float:
        """Rolling standard deviation of log returns."""
        close = data["close"].values
        if len(close) < self.volatility_lookback + 1:
            return 0.0
        log_returns = np.diff(np.log(close[-self.volatility_lookback - 1 :]))
        return float(np.std(log_returns))

    def _compute_spread(self, volatility: float) -> float:
        """Adaptive spread based on volatility."""
        spread = self.base_spread + self.volatility_multiplier * volatility
        return max(spread, self.min_spread)

    def _compute_skew(self) -> float:
        """Inventory skew: shifts quotes to reduce the heavy side."""
        if self.max_inventory == 0:
            return 0.0
        return self.skew_factor * (self._inventory / self.max_inventory)

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        if len(data) < self.required_history():
            return Signal.HOLD

        mid = data["close"].iloc[-1]

        # Don't quote near binary boundaries
        if mid < self.edge_buffer or mid > (1.0 - self.edge_buffer):
            return Signal.HOLD

        volatility = self._estimate_volatility(data)
        spread = self._compute_spread(volatility)
        self._last_spread = spread
        skew = self._compute_skew()

        # At max inventory, wait for exit
        if abs(self._inventory) >= self.max_inventory:
            return Signal.HOLD

        # Determine side based on inventory
        if self._inventory > 0:
            # Long inventory — post ask to reduce
            self._inventory -= 1
            return Signal.SELL
        elif self._inventory < 0:
            # Short inventory — post bid to reduce
            self._inventory += 1
            return Signal.BUY
        else:
            # Flat — alternate starting with BUY (post bid)
            self._inventory += 1
            self._bars_since_entry = 0
            return Signal.BUY

    def should_exit(self, position: Position, data: pd.DataFrame) -> bool:
        self._bars_since_entry += 1
        current_price = data["close"].iloc[-1]

        # Boundary exit
        if current_price < self.edge_buffer or current_price > (1.0 - self.edge_buffer):
            return True

        # Spread capture: price moved favorably by half the spread
        half_spread = self._last_spread / 2.0
        if position.side == "BUY":
            if current_price >= position.entry_price + half_spread:
                return True
        else:
            if current_price <= position.entry_price - half_spread:
                return True

        # Time limit
        if self._bars_since_entry >= self.max_hold_bars:
            return True

        # Stop loss
        if position.pnl_pct <= -self.inventory_stop_loss:
            return True

        return False
