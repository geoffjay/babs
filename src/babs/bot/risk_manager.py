"""Risk management: drawdown limits, position limits, daily loss limits."""

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import List

from babs.config.settings import RiskParams, DEFAULT_SETTINGS
from babs.strategies.base_strategy import Position

logger = logging.getLogger(__name__)


@dataclass
class DailyStats:
    date: date
    realized_pnl: float = 0.0
    trades_today: int = 0


class RiskManager:
    """Enforce risk limits before allowing new trades."""

    def __init__(self, params: RiskParams = DEFAULT_SETTINGS.risk, initial_capital: float = 1000.0):
        self.params = params
        self.initial_capital = initial_capital
        self.peak_equity = initial_capital
        self.current_equity = initial_capital
        self._daily_stats = DailyStats(date=date.today())

    def _ensure_today(self) -> None:
        """Reset daily counters if a new day has started."""
        today = date.today()
        if self._daily_stats.date != today:
            self._daily_stats = DailyStats(date=today)

    def update_equity(self, equity: float) -> None:
        """Update current equity and track the peak."""
        self.current_equity = equity
        if equity > self.peak_equity:
            self.peak_equity = equity

    def record_trade_pnl(self, pnl: float) -> None:
        """Record a closed trade's PnL for daily tracking."""
        self._ensure_today()
        self._daily_stats.realized_pnl += pnl
        self._daily_stats.trades_today += 1

    @property
    def current_drawdown(self) -> float:
        """Current drawdown as a fraction of peak equity."""
        if self.peak_equity <= 0:
            return 0.0
        return (self.peak_equity - self.current_equity) / self.peak_equity

    def can_trade(self, open_positions: List[Position]) -> bool:
        """Check all risk limits and return whether a new trade is allowed.

        Args:
            open_positions: List of currently open positions.

        Returns:
            True if trading is permitted, False if any limit is breached.
        """
        self._ensure_today()

        # Max drawdown check
        if self.current_drawdown >= self.params.max_drawdown:
            logger.warning(
                "RISK BLOCK: max drawdown breached (%.2f%% >= %.2f%%)",
                self.current_drawdown * 100, self.params.max_drawdown * 100,
            )
            return False

        # Max open positions
        if len(open_positions) >= self.params.max_open_positions:
            logger.warning(
                "RISK BLOCK: max open positions reached (%d >= %d)",
                len(open_positions), self.params.max_open_positions,
            )
            return False

        # Daily loss limit
        if self._daily_stats.realized_pnl <= -self.params.max_daily_loss:
            logger.warning(
                "RISK BLOCK: daily loss limit hit ($%.2f <= -$%.2f)",
                self._daily_stats.realized_pnl, self.params.max_daily_loss,
            )
            return False

        return True

    def validate_order_size(self, price: float, size: float) -> float:
        """Clamp order size to respect max position size.

        Returns the adjusted size (may be reduced or zero).
        """
        notional = price * size
        if notional > self.params.max_position_size:
            adjusted = self.params.max_position_size / price if price > 0 else 0.0
            logger.info(
                "Order size reduced: %.2f -> %.2f (max notional $%.2f)",
                size, adjusted, self.params.max_position_size,
            )
            return adjusted
        return size

    def status(self) -> dict:
        """Return a snapshot of current risk state."""
        self._ensure_today()
        return {
            "current_equity": self.current_equity,
            "peak_equity": self.peak_equity,
            "drawdown_pct": self.current_drawdown,
            "daily_pnl": self._daily_stats.realized_pnl,
            "trades_today": self._daily_stats.trades_today,
        }
