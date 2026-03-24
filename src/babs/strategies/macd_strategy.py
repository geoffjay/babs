"""MACD Histogram strategy with fast=3, slow=15, signal=3."""

import logging

import pandas as pd
import ta

from babs.config.settings import DEFAULT_SETTINGS
from babs.strategies.base_strategy import BaseStrategy, Position, Signal

logger = logging.getLogger(__name__)


class MACDStrategy(BaseStrategy):
    """MACD crossover strategy tuned for short-term Polymarket movements.

    Entry: MACD line crosses above signal line -> BUY
           MACD line crosses below signal line -> SELL
    Exit:  Reverse crossover, or stop-loss / take-profit hit.
    """

    name = "macd"

    def __init__(
        self,
        fast: int = DEFAULT_SETTINGS.macd.fast,
        slow: int = DEFAULT_SETTINGS.macd.slow,
        signal: int = DEFAULT_SETTINGS.macd.signal,
        stop_loss_pct: float = DEFAULT_SETTINGS.risk.stop_loss_pct,
        take_profit_pct: float = DEFAULT_SETTINGS.risk.take_profit_pct,
    ):
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

    def required_history(self) -> int:
        return self.slow + self.signal + 5

    def _compute_macd(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add MACD, signal, and histogram columns to data."""
        indicator = ta.trend.MACD(
            close=data["close"],
            window_slow=self.slow,
            window_fast=self.fast,
            window_sign=self.signal,
        )
        data = data.copy()
        data["macd"] = indicator.macd()
        data["macd_signal"] = indicator.macd_signal()
        data["macd_hist"] = indicator.macd_diff()
        return data

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        if len(data) < self.required_history():
            return Signal.HOLD

        df = self._compute_macd(data)

        current_hist = df["macd_hist"].iloc[-1]
        prev_hist = df["macd_hist"].iloc[-2]

        # Crossover detection via histogram sign change
        if prev_hist <= 0 and current_hist > 0:
            logger.info("MACD bullish crossover detected (hist: %.6f -> %.6f)", prev_hist, current_hist)
            return Signal.BUY
        elif prev_hist >= 0 and current_hist < 0:
            logger.info("MACD bearish crossover detected (hist: %.6f -> %.6f)", prev_hist, current_hist)
            return Signal.SELL

        return Signal.HOLD

    def should_exit(self, position: Position, data: pd.DataFrame) -> bool:
        # Stop-loss / take-profit
        if position.pnl_pct <= -self.stop_loss_pct:
            logger.info("MACD exit: stop-loss hit (pnl_pct=%.4f)", position.pnl_pct)
            return True
        if position.pnl_pct >= self.take_profit_pct:
            logger.info("MACD exit: take-profit hit (pnl_pct=%.4f)", position.pnl_pct)
            return True

        # Reverse crossover
        signal = self.generate_signal(data)
        if position.side == "BUY" and signal == Signal.SELL:
            logger.info("MACD exit: reverse crossover (long -> sell signal)")
            return True
        if position.side == "SELL" and signal == Signal.BUY:
            logger.info("MACD exit: reverse crossover (short -> buy signal)")
            return True

        return False
