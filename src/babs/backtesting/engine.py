"""Backtest engine: simulate strategy execution on historical data."""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

from babs.strategies.base_strategy import BaseStrategy, Position, Signal

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: Optional[pd.Timestamp]
    side: str
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    pnl_pct: float


@dataclass
class BacktestResult:
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    timestamps: List[pd.Timestamp] = field(default_factory=list)
    initial_capital: float = 0.0
    final_capital: float = 0.0


class BacktestEngine:
    """Simulates strategy execution on historical OHLCV data using limit orders only."""

    def __init__(
        self,
        strategy: BaseStrategy,
        initial_capital: float = 1000.0,
        position_size: float = 1.0,
        slippage_pct: float = 0.001,
        maker_mode: bool = False,
    ):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.slippage_pct = 0.0 if maker_mode else slippage_pct

    def run(self, data: pd.DataFrame) -> BacktestResult:
        """Run the backtest over the provided OHLCV data.

        Simulates limit order fills at the open price of the next bar (assuming
        the limit order would rest and fill at that level).

        Args:
            data: OHLCV DataFrame indexed by timestamp.

        Returns:
            BacktestResult with trades and equity curve.
        """
        result = BacktestResult(initial_capital=self.initial_capital)
        capital = self.initial_capital
        position: Optional[Position] = None
        min_bars = self.strategy.required_history()

        equity_curve = []
        timestamps = []

        for i in range(min_bars, len(data)):
            current_bar = data.iloc[i]
            history = data.iloc[: i + 1]
            current_time = data.index[i]
            current_price = current_bar["close"]

            # Update position's current price
            if position is not None:
                position.current_price = current_price

            # Check exit first
            if position is not None:
                if self.strategy.should_exit(position, history):
                    # Simulate limit exit at close with slippage
                    if position.side == "BUY":
                        exit_price = current_price * (1 - self.slippage_pct)
                        pnl = (exit_price - position.entry_price) * position.size
                    else:
                        exit_price = current_price * (1 + self.slippage_pct)
                        pnl = (position.entry_price - exit_price) * position.size

                    pnl_pct = pnl / (position.entry_price * position.size) if position.entry_price > 0 else 0

                    trade = Trade(
                        entry_time=position.entry_time,
                        exit_time=current_time,
                        side=position.side,
                        entry_price=position.entry_price,
                        exit_price=exit_price,
                        size=position.size,
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                    )
                    result.trades.append(trade)
                    capital += pnl
                    logger.debug(
                        "Closed %s @ %.4f -> %.4f, PnL=%.4f",
                        position.side, position.entry_price, exit_price, pnl,
                    )
                    position = None

            # Check entry if flat
            if position is None:
                signal = self.strategy.generate_signal(history)
                if signal in (Signal.BUY, Signal.SELL):
                    side = "BUY" if signal == Signal.BUY else "SELL"
                    # Simulate limit fill at close with slippage
                    if side == "BUY":
                        entry_price = current_price * (1 + self.slippage_pct)
                    else:
                        entry_price = current_price * (1 - self.slippage_pct)

                    size = self.position_size
                    if entry_price * size > capital:
                        size = capital / entry_price if entry_price > 0 else 0

                    if size > 0:
                        position = Position(
                            token_id="backtest",
                            side=side,
                            entry_price=entry_price,
                            size=size,
                            current_price=current_price,
                            entry_time=current_time,
                        )
                        logger.debug("Opened %s @ %.4f, size=%.4f", side, entry_price, size)

            # Track equity
            unrealized = position.unrealized_pnl if position else 0.0
            equity_curve.append(capital + unrealized)
            timestamps.append(current_time)

        # Close any remaining position at the last bar
        if position is not None:
            last_price = data["close"].iloc[-1]
            if position.side == "BUY":
                pnl = (last_price - position.entry_price) * position.size
            else:
                pnl = (position.entry_price - last_price) * position.size

            pnl_pct = pnl / (position.entry_price * position.size) if position.entry_price > 0 else 0
            trade = Trade(
                entry_time=position.entry_time,
                exit_time=data.index[-1],
                side=position.side,
                entry_price=position.entry_price,
                exit_price=last_price,
                size=position.size,
                pnl=pnl,
                pnl_pct=pnl_pct,
            )
            result.trades.append(trade)
            capital += pnl

        result.equity_curve = equity_curve
        result.timestamps = timestamps
        result.final_capital = capital

        logger.info(
            "Backtest complete: %d trades, final capital=%.2f (%.2f%%)",
            len(result.trades),
            capital,
            ((capital - self.initial_capital) / self.initial_capital) * 100,
        )
        return result
