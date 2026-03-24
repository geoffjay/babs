"""Cumulative Volume Delta (CVD) divergence strategy."""

import logging

import numpy as np
import pandas as pd

from babs.config.settings import DEFAULT_SETTINGS
from babs.strategies.base_strategy import BaseStrategy, Position, Signal

logger = logging.getLogger(__name__)


class CVDStrategy(BaseStrategy):
    """Cumulative Volume Delta divergence strategy.

    The CVD approximates buying vs selling pressure. When price and CVD diverge,
    it signals a potential reversal.

    Entry:
        Price drops but CVD rises -> hidden buying pressure -> BUY
        Price rises but CVD falls -> hidden selling pressure -> SELL
    Exit:
        Divergence resolves, or stop-loss/take-profit.
    """

    name = "cvd"

    def __init__(
        self,
        lookback: int = DEFAULT_SETTINGS.cvd.lookback,
        divergence_threshold: float = DEFAULT_SETTINGS.cvd.divergence_threshold,
        stop_loss_pct: float = DEFAULT_SETTINGS.risk.stop_loss_pct,
        take_profit_pct: float = DEFAULT_SETTINGS.risk.take_profit_pct,
    ):
        self.lookback = lookback
        self.divergence_threshold = divergence_threshold
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

    def required_history(self) -> int:
        return self.lookback + 10

    @staticmethod
    def _estimate_volume_delta(data: pd.DataFrame) -> pd.Series:
        """Estimate per-bar volume delta from OHLCV data.

        Uses the close-open ratio within the high-low range to split volume
        into buy and sell components.
        """
        hl_range = data["high"] - data["low"]
        # Avoid division by zero
        hl_range = hl_range.replace(0, np.nan)
        buy_ratio = (data["close"] - data["low"]) / hl_range
        buy_ratio = buy_ratio.fillna(0.5)
        buy_volume = data["volume"] * buy_ratio
        sell_volume = data["volume"] * (1 - buy_ratio)
        delta = buy_volume - sell_volume
        return delta

    def _compute_cvd(self, data: pd.DataFrame) -> pd.Series:
        """Compute cumulative volume delta."""
        delta = self._estimate_volume_delta(data)
        return delta.cumsum()

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        if len(data) < self.required_history():
            return Signal.HOLD

        window = data.tail(self.lookback).copy()
        cvd = self._compute_cvd(window)

        # Measure direction of price and CVD over the lookback period
        price_change = (window["close"].iloc[-1] - window["close"].iloc[0]) / window["close"].iloc[0]
        cvd_change = cvd.iloc[-1] - cvd.iloc[0]

        # Normalize CVD change relative to total volume
        total_volume = window["volume"].sum()
        if total_volume == 0:
            return Signal.HOLD
        cvd_change_norm = cvd_change / total_volume

        # Bullish divergence: price down but CVD up
        if price_change < -self.divergence_threshold and cvd_change_norm > self.divergence_threshold:
            logger.info(
                "CVD bullish divergence: price_change=%.4f, cvd_norm=%.4f",
                price_change, cvd_change_norm,
            )
            return Signal.BUY

        # Bearish divergence: price up but CVD down
        if price_change > self.divergence_threshold and cvd_change_norm < -self.divergence_threshold:
            logger.info(
                "CVD bearish divergence: price_change=%.4f, cvd_norm=%.4f",
                price_change, cvd_change_norm,
            )
            return Signal.SELL

        return Signal.HOLD

    def should_exit(self, position: Position, data: pd.DataFrame) -> bool:
        # Stop-loss / take-profit
        if position.pnl_pct <= -self.stop_loss_pct:
            logger.info("CVD exit: stop-loss hit (pnl_pct=%.4f)", position.pnl_pct)
            return True
        if position.pnl_pct >= self.take_profit_pct:
            logger.info("CVD exit: take-profit hit (pnl_pct=%.4f)", position.pnl_pct)
            return True

        # Check if divergence has resolved
        if len(data) < self.lookback:
            return False

        window = data.tail(self.lookback).copy()
        cvd = self._compute_cvd(window)
        price_change = (window["close"].iloc[-1] - window["close"].iloc[0]) / window["close"].iloc[0]
        cvd_change = cvd.iloc[-1] - cvd.iloc[0]
        total_volume = window["volume"].sum()
        if total_volume == 0:
            return False
        cvd_change_norm = cvd_change / total_volume

        # Divergence resolved: both moving in the same direction
        if position.side == "BUY" and price_change > 0 and cvd_change_norm > 0:
            logger.info("CVD exit: bullish divergence resolved")
            return True
        if position.side == "SELL" and price_change < 0 and cvd_change_norm < 0:
            logger.info("CVD exit: bearish divergence resolved")
            return True

        return False
