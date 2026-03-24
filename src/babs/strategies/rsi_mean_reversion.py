"""RSI Mean Reversion + VWAP strategy."""

import logging

import numpy as np
import pandas as pd
import ta

from babs.config.settings import DEFAULT_SETTINGS
from babs.strategies.base_strategy import BaseStrategy, Position, Signal

logger = logging.getLogger(__name__)


class RSIMeanReversionStrategy(BaseStrategy):
    """Mean reversion strategy using RSI and VWAP.

    Entry: RSI < oversold threshold (30) -> BUY (oversold bounce).
           RSI > overbought threshold (70) -> SELL (overbought fade).
    Exit:  RSI reverts to 50, or price reaches VWAP, or stop-loss/take-profit.
    """

    name = "rsi"

    def __init__(
        self,
        period: int = DEFAULT_SETTINGS.rsi.period,
        oversold: float = DEFAULT_SETTINGS.rsi.oversold,
        overbought: float = DEFAULT_SETTINGS.rsi.overbought,
        stop_loss_pct: float = DEFAULT_SETTINGS.risk.stop_loss_pct,
        take_profit_pct: float = DEFAULT_SETTINGS.risk.take_profit_pct,
    ):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

    def required_history(self) -> int:
        return self.period + 10

    @staticmethod
    def _compute_vwap(data: pd.DataFrame) -> pd.Series:
        """Compute session VWAP (Volume Weighted Average Price)."""
        typical_price = (data["high"] + data["low"] + data["close"]) / 3
        cumulative_tp_vol = (typical_price * data["volume"]).cumsum()
        cumulative_vol = data["volume"].cumsum()
        vwap = cumulative_tp_vol / cumulative_vol.replace(0, np.nan)
        return vwap.fillna(typical_price)

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        if len(data) < self.required_history():
            return Signal.HOLD

        rsi_indicator = ta.momentum.RSIIndicator(close=data["close"], window=self.period)
        rsi = rsi_indicator.rsi()
        current_rsi = rsi.iloc[-1]

        if np.isnan(current_rsi):
            return Signal.HOLD

        if current_rsi < self.oversold:
            logger.info("RSI oversold signal: RSI=%.2f < %.2f", current_rsi, self.oversold)
            return Signal.BUY
        elif current_rsi > self.overbought:
            logger.info("RSI overbought signal: RSI=%.2f > %.2f", current_rsi, self.overbought)
            return Signal.SELL

        return Signal.HOLD

    def should_exit(self, position: Position, data: pd.DataFrame) -> bool:
        # Stop-loss / take-profit
        if position.pnl_pct <= -self.stop_loss_pct:
            logger.info("RSI exit: stop-loss hit (pnl_pct=%.4f)", position.pnl_pct)
            return True
        if position.pnl_pct >= self.take_profit_pct:
            logger.info("RSI exit: take-profit hit (pnl_pct=%.4f)", position.pnl_pct)
            return True

        # RSI mean reversion to neutral
        rsi_indicator = ta.momentum.RSIIndicator(close=data["close"], window=self.period)
        rsi = rsi_indicator.rsi()
        current_rsi = rsi.iloc[-1]

        if position.side == "BUY" and current_rsi > 50:
            logger.info("RSI exit: RSI reverted above 50 (%.2f)", current_rsi)
            return True
        if position.side == "SELL" and current_rsi < 50:
            logger.info("RSI exit: RSI reverted below 50 (%.2f)", current_rsi)
            return True

        # Price reached VWAP
        vwap = self._compute_vwap(data)
        current_price = data["close"].iloc[-1]
        current_vwap = vwap.iloc[-1]

        if position.side == "BUY" and current_price >= current_vwap:
            logger.info("RSI exit: price (%.4f) reached VWAP (%.4f)", current_price, current_vwap)
            return True
        if position.side == "SELL" and current_price <= current_vwap:
            logger.info("RSI exit: price (%.4f) reached VWAP (%.4f)", current_price, current_vwap)
            return True

        return False
