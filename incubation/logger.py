"""Trade logging to CSV."""

import csv
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class TradeLogger:
    """Append trade records to a CSV file."""

    FIELDS = [
        "timestamp",
        "strategy",
        "token_id",
        "side",
        "price",
        "size",
        "pnl",
        "account",
        "notes",
    ]

    def __init__(self, filepath: str = "data/trades.csv"):
        self.filepath = filepath
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Create the CSV with headers if it doesn't exist."""
        path = Path(self.filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDS)
                writer.writeheader()
            logger.info("Created trade log at %s", self.filepath)

    def log_trade(
        self,
        strategy: str,
        token_id: str,
        side: str,
        price: float,
        size: float,
        pnl: float = 0.0,
        account: str = "",
        notes: str = "",
        timestamp: Optional[str] = None,
    ) -> None:
        """Append a single trade record to the CSV.

        Args:
            strategy: Name of the strategy that generated the trade.
            token_id: Market token identifier.
            side: "BUY" or "SELL".
            price: Execution price.
            size: Order size.
            pnl: Realized PnL (0 for entries).
            account: Account name used.
            notes: Optional notes.
            timestamp: ISO timestamp; defaults to now.
        """
        ts = timestamp or datetime.utcnow().isoformat()
        row = {
            "timestamp": ts,
            "strategy": strategy,
            "token_id": token_id,
            "side": side,
            "price": price,
            "size": size,
            "pnl": pnl,
            "account": account,
            "notes": notes,
        }

        try:
            with open(self.filepath, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDS)
                writer.writerow(row)
            logger.debug("Logged trade: %s %s @ %.4f", side, token_id[:16], price)
        except IOError:
            logger.exception("Failed to write trade log")

    def read_all(self) -> list:
        """Read all logged trades as a list of dicts."""
        if not os.path.exists(self.filepath):
            return []
        with open(self.filepath, "r") as f:
            reader = csv.DictReader(f)
            return list(reader)
