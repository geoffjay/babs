"""Position and P&L tracking."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TrackedPosition:
    token_id: str
    side: str
    entry_price: float
    size: float
    entry_time: datetime
    current_price: float = 0.0
    account: str = ""

    @property
    def unrealized_pnl(self) -> float:
        if self.side == "BUY":
            return (self.current_price - self.entry_price) * self.size
        return (self.entry_price - self.current_price) * self.size

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.entry_price == 0:
            return 0.0
        if self.side == "BUY":
            return (self.current_price - self.entry_price) / self.entry_price
        return (self.entry_price - self.current_price) / self.entry_price


@dataclass
class ClosedTrade:
    token_id: str
    side: str
    entry_price: float
    exit_price: float
    size: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    account: str = ""


class PositionTracker:
    """Track open positions and realized/unrealized P&L."""

    def __init__(self):
        self._open_positions: Dict[str, TrackedPosition] = {}
        self._closed_trades: List[ClosedTrade] = []
        self._total_realized_pnl: float = 0.0

    def open_position(
        self,
        token_id: str,
        side: str,
        entry_price: float,
        size: float,
        account: str = "",
    ) -> TrackedPosition:
        """Record a new open position."""
        pos = TrackedPosition(
            token_id=token_id,
            side=side,
            entry_price=entry_price,
            size=size,
            entry_time=datetime.utcnow(),
            current_price=entry_price,
            account=account,
        )
        self._open_positions[token_id] = pos
        logger.info(
            "Position opened: %s %s @ %.4f x %.2f",
            side, token_id[:16], entry_price, size,
        )
        return pos

    def close_position(self, token_id: str, exit_price: float) -> Optional[ClosedTrade]:
        """Close an open position and record the realized P&L."""
        pos = self._open_positions.pop(token_id, None)
        if pos is None:
            logger.warning("No open position found for token %s", token_id[:16])
            return None

        if pos.side == "BUY":
            pnl = (exit_price - pos.entry_price) * pos.size
        else:
            pnl = (pos.entry_price - exit_price) * pos.size

        trade = ClosedTrade(
            token_id=token_id,
            side=pos.side,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            size=pos.size,
            entry_time=pos.entry_time,
            exit_time=datetime.utcnow(),
            pnl=pnl,
            account=pos.account,
        )
        self._closed_trades.append(trade)
        self._total_realized_pnl += pnl

        logger.info(
            "Position closed: %s %s @ %.4f -> %.4f, PnL=%.4f",
            pos.side, token_id[:16], pos.entry_price, exit_price, pnl,
        )
        return trade

    def update_price(self, token_id: str, price: float) -> None:
        """Update the current market price for an open position."""
        if token_id in self._open_positions:
            self._open_positions[token_id].current_price = price

    def get_open_positions(self) -> List[TrackedPosition]:
        """Return all open positions."""
        return list(self._open_positions.values())

    def get_position(self, token_id: str) -> Optional[TrackedPosition]:
        """Get a specific open position by token ID."""
        return self._open_positions.get(token_id)

    def has_position(self, token_id: str) -> bool:
        """Check if there's an open position for the given token."""
        return token_id in self._open_positions

    @property
    def total_unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self._open_positions.values())

    @property
    def total_realized_pnl(self) -> float:
        return self._total_realized_pnl

    @property
    def total_pnl(self) -> float:
        return self._total_realized_pnl + self.total_unrealized_pnl

    @property
    def closed_trades(self) -> List[ClosedTrade]:
        return list(self._closed_trades)

    def summary(self) -> dict:
        """Return a summary of current tracking state."""
        return {
            "open_positions": len(self._open_positions),
            "closed_trades": len(self._closed_trades),
            "unrealized_pnl": self.total_unrealized_pnl,
            "realized_pnl": self.total_realized_pnl,
            "total_pnl": self.total_pnl,
        }
