"""Tests for risk manager."""

import unittest

from bot.risk_manager import RiskManager
from config.settings import RiskParams
from strategies.base_strategy import Position


class TestRiskManager(unittest.TestCase):
    def setUp(self):
        self.params = RiskParams(
            max_drawdown=0.20,
            stop_loss_pct=0.05,
            take_profit_pct=0.10,
            max_position_size=100.0,
            max_daily_loss=50.0,
            max_open_positions=5,
        )
        self.rm = RiskManager(params=self.params, initial_capital=1000.0)

    def test_can_trade_initially(self):
        self.assertTrue(self.rm.can_trade([]))

    def test_blocks_on_max_drawdown(self):
        self.rm.update_equity(1000.0)
        self.rm.update_equity(750.0)  # 25% drawdown > 20% limit
        self.assertFalse(self.rm.can_trade([]))

    def test_allows_within_drawdown(self):
        self.rm.update_equity(1000.0)
        self.rm.update_equity(850.0)  # 15% drawdown < 20% limit
        self.assertTrue(self.rm.can_trade([]))

    def test_blocks_on_max_positions(self):
        positions = [
            Position(f"token_{i}", "BUY", 0.50, 10.0)
            for i in range(5)
        ]
        self.assertFalse(self.rm.can_trade(positions))

    def test_allows_under_max_positions(self):
        positions = [
            Position(f"token_{i}", "BUY", 0.50, 10.0)
            for i in range(3)
        ]
        self.assertTrue(self.rm.can_trade(positions))

    def test_blocks_on_daily_loss(self):
        self.rm.record_trade_pnl(-30.0)
        self.rm.record_trade_pnl(-25.0)  # Total daily loss = -55 > -50 limit
        self.assertFalse(self.rm.can_trade([]))

    def test_validate_order_size_within_limit(self):
        size = self.rm.validate_order_size(0.50, 10.0)
        self.assertEqual(size, 10.0)

    def test_validate_order_size_clamped(self):
        size = self.rm.validate_order_size(0.50, 500.0)
        # Max notional is 100, so size = 100 / 0.50 = 200
        self.assertEqual(size, 200.0)

    def test_current_drawdown(self):
        self.rm.update_equity(1000.0)
        self.rm.update_equity(900.0)
        self.assertAlmostEqual(self.rm.current_drawdown, 0.10)

    def test_status_returns_dict(self):
        status = self.rm.status()
        self.assertIn("current_equity", status)
        self.assertIn("peak_equity", status)
        self.assertIn("drawdown_pct", status)
        self.assertIn("daily_pnl", status)
        self.assertIn("trades_today", status)


if __name__ == "__main__":
    unittest.main()
