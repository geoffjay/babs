"""Tests for the market making strategy."""

import unittest

import numpy as np
import pandas as pd

from babs.strategies.base_strategy import Signal, Position
from babs.strategies.market_making_strategy import MarketMakingStrategy
from babs.backtesting.engine import BacktestEngine


def _make_ohlcv(prices: list, volumes: list = None) -> pd.DataFrame:
    """Create a simple OHLCV DataFrame from a list of close prices."""
    n = len(prices)
    if volumes is None:
        volumes = [100.0] * n
    data = {
        "open": prices,
        "high": [p * 1.01 for p in prices],
        "low": [p * 0.99 for p in prices],
        "close": prices,
        "volume": volumes,
    }
    index = pd.date_range("2024-01-01", periods=n, freq="h")
    return pd.DataFrame(data, index=index)


class TestMarketMakingSignal(unittest.TestCase):
    def setUp(self):
        self.strategy = MarketMakingStrategy()

    def test_hold_on_insufficient_data(self):
        data = _make_ohlcv([0.50] * 5)
        self.assertEqual(self.strategy.generate_signal(data), Signal.HOLD)

    def test_hold_near_zero_boundary(self):
        data = _make_ohlcv([0.01] * 30)
        self.assertEqual(self.strategy.generate_signal(data), Signal.HOLD)

    def test_hold_near_one_boundary(self):
        data = _make_ohlcv([0.98] * 30)
        self.assertEqual(self.strategy.generate_signal(data), Signal.HOLD)

    def test_buy_when_flat(self):
        data = _make_ohlcv([0.50] * 30)
        signal = self.strategy.generate_signal(data)
        self.assertEqual(signal, Signal.BUY)

    def test_side_alternation(self):
        """After a BUY entry, next signal should be SELL to cycle inventory."""
        strategy = MarketMakingStrategy()
        data = _make_ohlcv([0.50] * 30)

        # First signal: BUY (flat -> long 1)
        sig1 = strategy.generate_signal(data)
        self.assertEqual(sig1, Signal.BUY)

        # Simulate that we exited the position — inventory is now +1
        # Next signal should be SELL to reduce inventory
        sig2 = strategy.generate_signal(data)
        self.assertEqual(sig2, Signal.SELL)

    def test_hold_at_max_inventory(self):
        strategy = MarketMakingStrategy(max_inventory=2.0)
        data = _make_ohlcv([0.50] * 30)

        # Build up inventory to max
        strategy._inventory = 2.0
        signal = strategy.generate_signal(data)
        self.assertEqual(signal, Signal.HOLD)


class TestMarketMakingExit(unittest.TestCase):
    def test_spread_capture_buy(self):
        strategy = MarketMakingStrategy(base_spread=0.02)
        strategy._last_spread = 0.02
        pos = Position(
            token_id="test", side="BUY",
            entry_price=0.50, size=10.0, current_price=0.52,
        )
        # Price moved up by 0.02, half spread is 0.01 => captured
        data = _make_ohlcv([0.50] * 29 + [0.52])
        self.assertTrue(strategy.should_exit(pos, data))

    def test_spread_capture_sell(self):
        strategy = MarketMakingStrategy(base_spread=0.02)
        strategy._last_spread = 0.02
        pos = Position(
            token_id="test", side="SELL",
            entry_price=0.50, size=10.0, current_price=0.48,
        )
        data = _make_ohlcv([0.50] * 29 + [0.48])
        self.assertTrue(strategy.should_exit(pos, data))

    def test_max_hold_bars_timeout(self):
        strategy = MarketMakingStrategy(max_hold_bars=3)
        strategy._last_spread = 0.02
        pos = Position(
            token_id="test", side="BUY",
            entry_price=0.50, size=10.0, current_price=0.50,
        )
        data = _make_ohlcv([0.50] * 30)
        # Simulate bars passing
        for _ in range(2):
            self.assertFalse(strategy.should_exit(pos, data))
        self.assertTrue(strategy.should_exit(pos, data))

    def test_stop_loss(self):
        strategy = MarketMakingStrategy(inventory_stop_loss=0.05)
        strategy._last_spread = 0.02
        pos = Position(
            token_id="test", side="BUY",
            entry_price=0.50, size=10.0, current_price=0.46,
        )
        # pnl_pct = (0.46 - 0.50) / 0.50 = -0.08, exceeds 0.05
        data = _make_ohlcv([0.50] * 29 + [0.46])
        self.assertTrue(strategy.should_exit(pos, data))

    def test_boundary_exit(self):
        strategy = MarketMakingStrategy(edge_buffer=0.03)
        strategy._last_spread = 0.02
        pos = Position(
            token_id="test", side="BUY",
            entry_price=0.50, size=10.0, current_price=0.02,
        )
        data = _make_ohlcv([0.50] * 29 + [0.02])
        self.assertTrue(strategy.should_exit(pos, data))

    def test_no_exit_in_normal_conditions(self):
        strategy = MarketMakingStrategy(max_hold_bars=10)
        strategy._last_spread = 0.10  # wide spread so capture won't trigger
        strategy._bars_since_entry = 0
        pos = Position(
            token_id="test", side="BUY",
            entry_price=0.50, size=10.0, current_price=0.50,
        )
        data = _make_ohlcv([0.50] * 30)
        self.assertFalse(strategy.should_exit(pos, data))


class TestMarketMakingVolatility(unittest.TestCase):
    def test_volatility_on_flat_data(self):
        strategy = MarketMakingStrategy(volatility_lookback=20)
        data = _make_ohlcv([0.50] * 30)
        vol = strategy._estimate_volatility(data)
        self.assertAlmostEqual(vol, 0.0, places=5)

    def test_volatility_increases_with_movement(self):
        strategy = MarketMakingStrategy(volatility_lookback=20)
        # Alternating prices create higher volatility
        prices = [0.50 + (0.02 if i % 2 == 0 else -0.02) for i in range(30)]
        data = _make_ohlcv(prices)
        vol = strategy._estimate_volatility(data)
        self.assertGreater(vol, 0.01)

    def test_adaptive_spread_widens_with_volatility(self):
        strategy = MarketMakingStrategy(
            base_spread=0.02, volatility_multiplier=2.0, min_spread=0.01,
        )
        low_vol_spread = strategy._compute_spread(0.01)
        high_vol_spread = strategy._compute_spread(0.05)
        self.assertGreater(high_vol_spread, low_vol_spread)


class TestMarketMakingIntegration(unittest.TestCase):
    def test_backtest_produces_trades(self):
        """Run MM strategy through BacktestEngine and verify trades are generated."""
        strategy = MarketMakingStrategy(
            base_spread=0.02,
            max_hold_bars=5,
            volatility_lookback=10,
        )
        # Create price data with small oscillations around 0.50
        np.random.seed(42)
        base = 0.50
        noise = np.random.normal(0, 0.005, 100)
        prices = [base + n for n in noise]
        # Clamp to valid binary range
        prices = [max(0.05, min(0.95, p)) for p in prices]
        data = _make_ohlcv(prices)

        engine = BacktestEngine(
            strategy=strategy,
            initial_capital=1000.0,
            position_size=10.0,
            maker_mode=True,
        )
        result = engine.run(data)
        self.assertGreater(len(result.trades), 0)
        self.assertGreater(len(result.equity_curve), 0)

    def test_maker_mode_zero_slippage(self):
        """Verify maker_mode sets slippage to 0."""
        strategy = MarketMakingStrategy()
        engine = BacktestEngine(strategy=strategy, maker_mode=True)
        self.assertEqual(engine.slippage_pct, 0.0)

    def test_non_maker_mode_has_slippage(self):
        strategy = MarketMakingStrategy()
        engine = BacktestEngine(strategy=strategy, maker_mode=False)
        self.assertEqual(engine.slippage_pct, 0.001)


if __name__ == "__main__":
    unittest.main()
