"""Tests for backtest engine and metrics."""

import unittest

import pandas as pd

from babs.backtesting.engine import BacktestEngine, BacktestResult, Trade
from babs.backtesting.metrics import calculate_metrics, _compute_max_drawdown, _compute_sharpe
from babs.strategies.macd_strategy import MACDStrategy
from babs.strategies.rsi_mean_reversion import RSIMeanReversionStrategy


def _make_trending_data(n: int = 200, start_price: float = 0.50) -> pd.DataFrame:
    """Create OHLCV data with an up-then-down trend."""
    import numpy as np
    half = n // 2
    up = [start_price + i * 0.002 for i in range(half)]
    down = [up[-1] - i * 0.002 for i in range(n - half)]
    prices = up + down
    noise = np.random.normal(0, 0.001, n)
    prices = [max(0.01, p + n_) for p, n_ in zip(prices, noise)]

    data = {
        "open": prices,
        "high": [p * 1.005 for p in prices],
        "low": [p * 0.995 for p in prices],
        "close": prices,
        "volume": [1000.0] * n,
    }
    index = pd.date_range("2024-01-01", periods=n, freq="h")
    return pd.DataFrame(data, index=index)


class TestBacktestEngine(unittest.TestCase):
    def test_engine_runs_without_error(self):
        strategy = MACDStrategy()
        engine = BacktestEngine(strategy=strategy, initial_capital=1000.0, position_size=10.0)
        data = _make_trending_data(200)
        result = engine.run(data)

        self.assertIsInstance(result, BacktestResult)
        self.assertEqual(result.initial_capital, 1000.0)
        self.assertGreater(len(result.equity_curve), 0)

    def test_engine_with_rsi_strategy(self):
        strategy = RSIMeanReversionStrategy()
        engine = BacktestEngine(strategy=strategy, initial_capital=500.0, position_size=5.0)
        data = _make_trending_data(200)
        result = engine.run(data)

        self.assertIsInstance(result, BacktestResult)
        self.assertGreater(len(result.equity_curve), 0)

    def test_no_trades_on_flat_data(self):
        strategy = MACDStrategy()
        engine = BacktestEngine(strategy=strategy, initial_capital=1000.0)
        data = pd.DataFrame({
            "open": [0.50] * 100,
            "high": [0.505] * 100,
            "low": [0.495] * 100,
            "close": [0.50] * 100,
            "volume": [100.0] * 100,
        }, index=pd.date_range("2024-01-01", periods=100, freq="h"))

        result = engine.run(data)
        self.assertEqual(len(result.trades), 0)
        self.assertAlmostEqual(result.final_capital, 1000.0)


class TestMetrics(unittest.TestCase):
    def test_empty_result(self):
        result = BacktestResult(initial_capital=1000.0, final_capital=1000.0)
        metrics = calculate_metrics(result)
        self.assertEqual(metrics.total_trades, 0)
        self.assertEqual(metrics.win_rate, 0.0)

    def test_max_drawdown(self):
        equity = [100, 110, 105, 95, 100, 90, 110]
        dd, dd_pct = _compute_max_drawdown(equity)
        self.assertGreater(dd, 0)
        self.assertGreater(dd_pct, 0)

    def test_sharpe_ratio(self):
        # Steadily increasing equity should have a positive Sharpe
        equity = [100 + i for i in range(100)]
        sharpe = _compute_sharpe(equity)
        self.assertGreater(sharpe, 0)

    def test_metrics_with_trades(self):
        result = BacktestResult(
            initial_capital=1000.0,
            final_capital=1050.0,
            equity_curve=[1000, 1010, 1005, 1020, 1050],
        )
        result.trades = [
            Trade("2024-01-01", "2024-01-02", "BUY", 0.50, 0.52, 10, 0.20, 0.04),
            Trade("2024-01-03", "2024-01-04", "BUY", 0.48, 0.46, 10, -0.20, -0.04),
            Trade("2024-01-05", "2024-01-06", "SELL", 0.55, 0.50, 10, 0.50, 0.09),
        ]
        metrics = calculate_metrics(result)
        self.assertEqual(metrics.total_trades, 3)
        self.assertEqual(metrics.winning_trades, 2)
        self.assertEqual(metrics.losing_trades, 1)
        self.assertGreater(metrics.profit_factor, 1.0)


if __name__ == "__main__":
    unittest.main()
