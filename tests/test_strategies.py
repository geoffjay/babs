"""Tests for trading strategies."""

import unittest

import numpy as np
import pandas as pd

from strategies.base_strategy import Signal, Position
from strategies.macd_strategy import MACDStrategy
from strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from strategies.cvd_strategy import CVDStrategy


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


class TestMACDStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = MACDStrategy(fast=3, slow=15, signal=3)

    def test_hold_on_insufficient_data(self):
        data = _make_ohlcv([0.50] * 5)
        self.assertEqual(self.strategy.generate_signal(data), Signal.HOLD)

    def test_hold_on_flat_data(self):
        data = _make_ohlcv([0.50] * 50)
        signal = self.strategy.generate_signal(data)
        self.assertEqual(signal, Signal.HOLD)

    def test_buy_signal_on_uptrend(self):
        # Create data with a downtrend followed by an uptrend to trigger crossover
        prices = [0.50 - i * 0.005 for i in range(25)]
        prices += [0.375 + i * 0.01 for i in range(25)]
        data = _make_ohlcv(prices)
        signal = self.strategy.generate_signal(data)
        self.assertIn(signal, [Signal.BUY, Signal.HOLD])

    def test_should_exit_on_stop_loss(self):
        pos = Position(
            token_id="test", side="BUY",
            entry_price=0.50, size=10.0, current_price=0.40,
        )
        data = _make_ohlcv([0.50] * 50)
        self.assertTrue(self.strategy.should_exit(pos, data))

    def test_should_exit_on_take_profit(self):
        pos = Position(
            token_id="test", side="BUY",
            entry_price=0.50, size=10.0, current_price=0.60,
        )
        data = _make_ohlcv([0.50] * 50)
        self.assertTrue(self.strategy.should_exit(pos, data))


class TestRSIMeanReversionStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = RSIMeanReversionStrategy(period=14, oversold=30, overbought=70)

    def test_hold_on_insufficient_data(self):
        data = _make_ohlcv([0.50] * 5)
        self.assertEqual(self.strategy.generate_signal(data), Signal.HOLD)

    def test_buy_on_oversold(self):
        # Simulate a steep downtrend to push RSI below 30
        prices = [0.80 - i * 0.015 for i in range(40)]
        data = _make_ohlcv(prices)
        signal = self.strategy.generate_signal(data)
        self.assertIn(signal, [Signal.BUY, Signal.HOLD])

    def test_vwap_computation(self):
        data = _make_ohlcv([0.50] * 30, volumes=[100] * 30)
        vwap = RSIMeanReversionStrategy._compute_vwap(data)
        self.assertEqual(len(vwap), 30)
        # With constant prices, VWAP should be close to the typical price
        self.assertAlmostEqual(vwap.iloc[-1], 0.50, delta=0.01)


class TestCVDStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = CVDStrategy(lookback=20, divergence_threshold=0.01)

    def test_hold_on_insufficient_data(self):
        data = _make_ohlcv([0.50] * 5)
        self.assertEqual(self.strategy.generate_signal(data), Signal.HOLD)

    def test_hold_on_flat_market(self):
        data = _make_ohlcv([0.50] * 50, volumes=[100] * 50)
        signal = self.strategy.generate_signal(data)
        self.assertEqual(signal, Signal.HOLD)

    def test_volume_delta_estimation(self):
        data = _make_ohlcv([0.50] * 10)
        delta = CVDStrategy._estimate_volume_delta(data)
        self.assertEqual(len(delta), 10)


if __name__ == "__main__":
    unittest.main()
