"""Abstract base strategy class for all trading strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import pandas as pd


class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class Position:
    token_id: str
    side: str
    entry_price: float
    size: float
    current_price: float = 0.0
    entry_time: Optional[pd.Timestamp] = field(default=None, repr=False)

    @property
    def unrealized_pnl(self) -> float:
        if self.side == "BUY":
            return (self.current_price - self.entry_price) * self.size
        else:
            return (self.entry_price - self.current_price) * self.size

    @property
    def pnl_pct(self) -> float:
        if self.entry_price == 0:
            return 0.0
        if self.side == "BUY":
            return (self.current_price - self.entry_price) / self.entry_price
        else:
            return (self.entry_price - self.current_price) / self.entry_price


class BaseStrategy(ABC):
    """Abstract base class that all strategies must implement."""

    name: str = "base"

    @abstractmethod
    def generate_signal(self, data: pd.DataFrame) -> Signal:
        """Analyze market data and produce a trading signal.

        Args:
            data: OHLCV DataFrame with at least columns: open, high, low, close, volume.

        Returns:
            Signal.BUY, Signal.SELL, or Signal.HOLD.
        """
        ...

    @abstractmethod
    def should_exit(self, position: Position, data: pd.DataFrame) -> bool:
        """Determine whether an open position should be closed.

        Args:
            position: The current open position.
            data: Latest OHLCV data.

        Returns:
            True if the position should be exited.
        """
        ...

    def required_history(self) -> int:
        """Minimum number of candles the strategy needs to generate a signal."""
        return 50
