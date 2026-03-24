"""Position size scaling based on performance."""

import logging
from dataclasses import dataclass
from typing import List

from babs.bot.position_tracker import ClosedTrade

logger = logging.getLogger(__name__)


@dataclass
class ScalingConfig:
    base_size: float = 1.0
    min_size: float = 0.5
    max_size: float = 10.0
    scale_up_factor: float = 1.25
    scale_down_factor: float = 0.75
    evaluation_window: int = 20  # Number of recent trades to evaluate
    win_rate_threshold_up: float = 0.60  # Scale up if win rate exceeds this
    win_rate_threshold_down: float = 0.40  # Scale down if win rate falls below this
    profit_factor_threshold_up: float = 1.5
    profit_factor_threshold_down: float = 0.8


class PositionScaler:
    """Dynamically adjust position sizes based on recent trading performance.

    Increases size when the strategy is performing well and decreases when
    it's underperforming, providing a form of adaptive risk management.
    """

    def __init__(self, config: ScalingConfig = ScalingConfig()):
        self.config = config
        self.current_size = config.base_size

    def evaluate(self, trades: List[ClosedTrade]) -> float:
        """Evaluate recent performance and return the recommended position size.

        Args:
            trades: Complete list of closed trades (most recent last).

        Returns:
            The new recommended position size.
        """
        recent = trades[-self.config.evaluation_window:]
        if len(recent) < 5:
            logger.debug("Not enough trades (%d) for scaling evaluation", len(recent))
            return self.current_size

        wins = [t for t in recent if t.pnl > 0]
        losses = [t for t in recent if t.pnl <= 0]
        win_rate = len(wins) / len(recent)

        gross_profit = sum(t.pnl for t in wins) if wins else 0.0
        gross_loss = abs(sum(t.pnl for t in losses)) if losses else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        new_size = self.current_size

        # Scale up conditions
        if (
            win_rate >= self.config.win_rate_threshold_up
            and profit_factor >= self.config.profit_factor_threshold_up
        ):
            new_size = self.current_size * self.config.scale_up_factor
            logger.info(
                "Scaling UP: win_rate=%.1f%%, pf=%.2f -> size %.2f -> %.2f",
                win_rate * 100, profit_factor, self.current_size, new_size,
            )

        # Scale down conditions
        elif (
            win_rate <= self.config.win_rate_threshold_down
            or profit_factor <= self.config.profit_factor_threshold_down
        ):
            new_size = self.current_size * self.config.scale_down_factor
            logger.info(
                "Scaling DOWN: win_rate=%.1f%%, pf=%.2f -> size %.2f -> %.2f",
                win_rate * 100, profit_factor, self.current_size, new_size,
            )

        # Clamp to bounds
        new_size = max(self.config.min_size, min(self.config.max_size, new_size))
        self.current_size = new_size
        return new_size

    def reset(self) -> None:
        """Reset to base size."""
        self.current_size = self.config.base_size
        logger.info("Position scaler reset to base size %.2f", self.current_size)
