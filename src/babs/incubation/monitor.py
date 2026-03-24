"""Bot monitoring: display P&L, win rates, active positions."""

import logging
import time
from datetime import datetime
from typing import Dict, List

from babs.bot.position_tracker import PositionTracker

logger = logging.getLogger(__name__)


class BotMonitor:
    """Monitor running trading bots and display aggregate statistics."""

    def __init__(self):
        self._trackers: Dict[str, PositionTracker] = {}

    def register(self, bot_name: str, tracker: PositionTracker) -> None:
        """Register a bot's position tracker for monitoring."""
        self._trackers[bot_name] = tracker
        logger.info("Registered bot '%s' for monitoring", bot_name)

    def unregister(self, bot_name: str) -> None:
        """Remove a bot from monitoring."""
        self._trackers.pop(bot_name, None)

    def get_summary(self) -> List[dict]:
        """Collect summary data from all registered bots."""
        summaries = []
        for name, tracker in self._trackers.items():
            closed = tracker.closed_trades
            wins = sum(1 for t in closed if t.pnl > 0)
            total = len(closed)
            win_rate = wins / total if total > 0 else 0.0

            summaries.append({
                "bot": name,
                "open_positions": len(tracker.get_open_positions()),
                "total_trades": total,
                "win_rate": win_rate,
                "realized_pnl": tracker.total_realized_pnl,
                "unrealized_pnl": tracker.total_unrealized_pnl,
                "total_pnl": tracker.total_pnl,
            })
        return summaries

    def print_dashboard(self) -> None:
        """Print a formatted monitoring dashboard to stdout."""
        summaries = self.get_summary()

        print("\n" + "=" * 80)
        print(f"  BOT MONITORING DASHBOARD  |  {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print("=" * 80)

        if not summaries:
            print("  No bots registered.")
            print("=" * 80)
            return

        header = (
            f"{'Bot':<20} {'Pos':>4} {'Trades':>7} {'Win%':>7} "
            f"{'Real PnL':>10} {'Unrl PnL':>10} {'Total':>10}"
        )
        print(header)
        print("-" * 80)

        total_pnl = 0.0
        for s in summaries:
            row = (
                f"{s['bot']:<20} "
                f"{s['open_positions']:>4} "
                f"{s['total_trades']:>7} "
                f"{s['win_rate']:>6.1%} "
                f"${s['realized_pnl']:>9.2f} "
                f"${s['unrealized_pnl']:>9.2f} "
                f"${s['total_pnl']:>9.2f}"
            )
            print(row)
            total_pnl += s["total_pnl"]

        print("-" * 80)
        print(f"{'TOTAL':<20} {'':>4} {'':>7} {'':>7} {'':>10} {'':>10} ${total_pnl:>9.2f}")
        print("=" * 80 + "\n")

    def run_loop(self, interval_seconds: int = 30) -> None:
        """Continuously print the dashboard at the given interval."""
        logger.info("Starting monitoring loop (interval=%ds)", interval_seconds)
        try:
            while True:
                self.print_dashboard()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Monitoring stopped")
