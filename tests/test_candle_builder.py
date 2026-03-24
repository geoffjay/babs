"""Tests for candle_builder module."""

import unittest

import pandas as pd

from babs.data.candle_builder import Candle, CandleBuilder, Sample, parse_timeframe_seconds


class TestParseTimeframeSeconds(unittest.TestCase):
    def test_minutes(self):
        self.assertEqual(parse_timeframe_seconds("5m"), 300)

    def test_hours(self):
        self.assertEqual(parse_timeframe_seconds("1h"), 3600)

    def test_days(self):
        self.assertEqual(parse_timeframe_seconds("1d"), 86400)

    def test_seconds(self):
        self.assertEqual(parse_timeframe_seconds("30s"), 30)

    def test_invalid_unit(self):
        with self.assertRaises(ValueError):
            parse_timeframe_seconds("5x")


class TestCandleBuilderSingleSample(unittest.TestCase):
    def test_single_sample_creates_candle(self):
        builder = CandleBuilder(interval_seconds=300)
        sample = Sample(timestamp=1000.0, price=0.55, best_bid=0.54, best_ask=0.56,
                        bid_depth=100.0, ask_depth=80.0)
        builder.add_sample(sample)

        df = builder.get_dataframe()
        self.assertEqual(len(df), 1)
        row = df.iloc[0]
        self.assertAlmostEqual(row["open"], 0.55)
        self.assertAlmostEqual(row["high"], 0.56)  # best_ask widens high
        self.assertAlmostEqual(row["low"], 0.54)   # best_bid widens low
        self.assertAlmostEqual(row["close"], 0.55)
        self.assertAlmostEqual(row["volume"], 0.0)  # no prior depth to compare


class TestCandleBuilderMultipleSamples(unittest.TestCase):
    def setUp(self):
        self.builder = CandleBuilder(interval_seconds=300)

    def test_multiple_samples_same_interval(self):
        base_ts = 600.0  # falls in interval [600, 900)
        self.builder.add_sample(Sample(timestamp=base_ts, price=0.50,
                                       bid_depth=100.0, ask_depth=80.0))
        self.builder.add_sample(Sample(timestamp=base_ts + 30, price=0.55,
                                       bid_depth=90.0, ask_depth=70.0))
        self.builder.add_sample(Sample(timestamp=base_ts + 60, price=0.48,
                                       bid_depth=85.0, ask_depth=65.0))

        df = self.builder.get_dataframe()
        self.assertEqual(len(df), 1)
        row = df.iloc[0]
        self.assertAlmostEqual(row["open"], 0.50)
        self.assertAlmostEqual(row["high"], 0.55)
        self.assertAlmostEqual(row["low"], 0.48)
        self.assertAlmostEqual(row["close"], 0.48)

    def test_volume_estimation_from_depth_changes(self):
        base_ts = 600.0
        self.builder.add_sample(Sample(timestamp=base_ts, price=0.50,
                                       bid_depth=100.0, ask_depth=80.0))
        # Second sample: bid depth dropped by 10, ask depth dropped by 5
        self.builder.add_sample(Sample(timestamp=base_ts + 30, price=0.51,
                                       bid_depth=90.0, ask_depth=75.0))
        df = self.builder.get_dataframe()
        self.assertAlmostEqual(df.iloc[0]["volume"], 15.0)

    def test_volume_no_negative_contribution(self):
        """Depth increase should not add negative volume."""
        base_ts = 600.0
        self.builder.add_sample(Sample(timestamp=base_ts, price=0.50,
                                       bid_depth=100.0, ask_depth=80.0))
        # Depth increased (refill) — should not subtract from volume
        self.builder.add_sample(Sample(timestamp=base_ts + 30, price=0.51,
                                       bid_depth=120.0, ask_depth=90.0))
        df = self.builder.get_dataframe()
        self.assertAlmostEqual(df.iloc[0]["volume"], 0.0)


class TestCandleBuilderIntervalRollover(unittest.TestCase):
    def test_rollover_finalizes_previous_candle(self):
        builder = CandleBuilder(interval_seconds=300)
        # Interval 1: [0, 300)
        builder.add_sample(Sample(timestamp=100.0, price=0.50,
                                  bid_depth=100.0, ask_depth=80.0))
        # Interval 2: [300, 600)
        builder.add_sample(Sample(timestamp=400.0, price=0.60,
                                  bid_depth=95.0, ask_depth=75.0))

        df = builder.get_dataframe(include_current=False)
        # Only the first candle should be closed
        self.assertEqual(len(df), 1)
        self.assertAlmostEqual(df.iloc[0]["close"], 0.50)

        df_all = builder.get_dataframe(include_current=True)
        self.assertEqual(len(df_all), 2)
        self.assertAlmostEqual(df_all.iloc[1]["open"], 0.60)


class TestCandleBuilderBidAskWidening(unittest.TestCase):
    def test_best_ask_widens_high(self):
        builder = CandleBuilder(interval_seconds=300)
        builder.add_sample(Sample(timestamp=600.0, price=0.50,
                                  best_bid=0.49, best_ask=0.55))
        df = builder.get_dataframe()
        self.assertAlmostEqual(df.iloc[0]["high"], 0.55)

    def test_best_bid_widens_low(self):
        builder = CandleBuilder(interval_seconds=300)
        builder.add_sample(Sample(timestamp=600.0, price=0.50,
                                  best_bid=0.45, best_ask=0.51))
        df = builder.get_dataframe()
        self.assertAlmostEqual(df.iloc[0]["low"], 0.45)


class TestCandleBuilderSeedFromHistory(unittest.TestCase):
    def test_seed_creates_closed_candles(self):
        builder = CandleBuilder(interval_seconds=300)
        history = [
            {"t": 0, "p": 0.50},
            {"t": 300, "p": 0.52},
            {"t": 600, "p": 0.51},
        ]
        builder.seed_from_history(history)

        df = builder.get_dataframe(include_current=False)
        self.assertEqual(len(df), 3)  # all seeded candles are marked closed

    def test_seed_plus_live_sample(self):
        builder = CandleBuilder(interval_seconds=300)
        history = [
            {"t": 0, "p": 0.50},
            {"t": 300, "p": 0.52},
        ]
        builder.seed_from_history(history)

        # Live sample in a new interval
        builder.add_sample(Sample(timestamp=700.0, price=0.55,
                                  bid_depth=100.0, ask_depth=80.0))

        df = builder.get_dataframe(include_current=True)
        self.assertEqual(len(df), 3)
        self.assertAlmostEqual(df.iloc[-1]["close"], 0.55)

    def test_seed_skips_invalid_points(self):
        builder = CandleBuilder(interval_seconds=300)
        history = [
            {"t": 0, "p": 0.50},
            {"t": None, "p": 0.52},
            {"t": 300},  # missing p
        ]
        builder.seed_from_history(history)
        df = builder.get_dataframe()
        self.assertEqual(len(df), 1)


class TestCandleBuilderMaxCandles(unittest.TestCase):
    def test_bounded_by_deque(self):
        builder = CandleBuilder(interval_seconds=300, max_candles=5)
        history = [{"t": i * 300, "p": 0.50} for i in range(10)]
        builder.seed_from_history(history)

        df = builder.get_dataframe()
        self.assertEqual(len(df), 5)


class TestCandleBuilderFallbackFlatSample(unittest.TestCase):
    def test_flat_sample_no_crash(self):
        """A sample with no bid/ask data should not crash."""
        builder = CandleBuilder(interval_seconds=300)
        sample = Sample(timestamp=600.0, price=0.50)
        builder.add_sample(sample)

        df = builder.get_dataframe()
        self.assertEqual(len(df), 1)
        self.assertAlmostEqual(df.iloc[0]["open"], 0.50)
        self.assertAlmostEqual(df.iloc[0]["high"], 0.50)
        self.assertAlmostEqual(df.iloc[0]["low"], 0.50)


class TestCandleBuilderDataFrame(unittest.TestCase):
    def test_dataframe_columns_and_index(self):
        builder = CandleBuilder(interval_seconds=300)
        builder.add_sample(Sample(timestamp=600.0, price=0.50))

        df = builder.get_dataframe()
        self.assertListEqual(list(df.columns), ["open", "high", "low", "close", "volume"])
        self.assertEqual(df.index.name, "timestamp")

    def test_empty_builder_returns_empty_df(self):
        builder = CandleBuilder(interval_seconds=300)
        df = builder.get_dataframe()
        self.assertTrue(df.empty)
        self.assertListEqual(list(df.columns), ["open", "high", "low", "close", "volume"])


if __name__ == "__main__":
    unittest.main()
