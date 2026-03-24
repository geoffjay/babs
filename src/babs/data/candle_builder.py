"""Build real OHLCV candles from sub-candle order book polling."""

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Optional

import pandas as pd


@dataclass
class Sample:
    """A single observation from an order book poll."""

    timestamp: float  # unix seconds
    price: float
    best_bid: float = 0.0
    best_ask: float = 0.0
    bid_depth: float = 0.0
    ask_depth: float = 0.0


@dataclass
class Candle:
    """An OHLCV candle, possibly still accumulating samples."""

    timestamp: float  # interval-floored unix seconds
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    closed: bool = False


def parse_timeframe_seconds(tf: str) -> int:
    """Convert a timeframe string like '5m' or '1h' to seconds."""
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    suffix = tf[-1].lower()
    if suffix not in units:
        raise ValueError(f"Unknown timeframe unit: {tf!r}")
    return int(tf[:-1]) * units[suffix]


class CandleBuilder:
    """Accumulate order book samples into OHLCV candles."""

    def __init__(self, interval_seconds: int, max_candles: int = 200):
        self.interval = interval_seconds
        self.max_candles = max_candles
        self._candles: Deque[Candle] = deque(maxlen=max_candles)
        self._prev_bid_depth: Optional[float] = None
        self._prev_ask_depth: Optional[float] = None

    def _floor_ts(self, ts: float) -> float:
        return (ts // self.interval) * self.interval

    def add_sample(self, sample: Sample) -> None:
        """Incorporate a new sample into the candle series."""
        bucket = self._floor_ts(sample.timestamp)

        # Finalize any older candle
        if self._candles and not self._candles[-1].closed and self._candles[-1].timestamp < bucket:
            self._candles[-1].closed = True

        # Start new candle or update current
        if not self._candles or self._candles[-1].timestamp < bucket:
            candle = Candle(
                timestamp=bucket,
                open=sample.price,
                high=max(sample.price, sample.best_ask) if sample.best_ask else sample.price,
                low=min(sample.price, sample.best_bid) if sample.best_bid else sample.price,
                close=sample.price,
            )
            self._candles.append(candle)
        else:
            candle = self._candles[-1]
            high_candidate = max(sample.price, sample.best_ask) if sample.best_ask else sample.price
            low_candidate = min(sample.price, sample.best_bid) if sample.best_bid else sample.price
            candle.high = max(candle.high, high_candidate)
            candle.low = min(candle.low, low_candidate)
            candle.close = sample.price

        # Estimate volume from depth changes
        if self._prev_bid_depth is not None and self._prev_ask_depth is not None:
            bid_consumed = max(0.0, self._prev_bid_depth - sample.bid_depth)
            ask_consumed = max(0.0, self._prev_ask_depth - sample.ask_depth)
            candle.volume += bid_consumed + ask_consumed

        self._prev_bid_depth = sample.bid_depth
        self._prev_ask_depth = sample.ask_depth

    def seed_from_history(self, history: list) -> None:
        """Bootstrap from /prices-history data as flat candles.

        Args:
            history: List of dicts with 't' (unix timestamp) and 'p' (price).
        """
        for point in history:
            ts = point.get("t")
            price = point.get("p")
            if ts is None or price is None:
                continue
            price = float(price)
            candle = Candle(
                timestamp=float(ts),
                open=price,
                high=price,
                low=price,
                close=price,
                volume=0.0,
                closed=True,
            )
            self._candles.append(candle)

    def get_dataframe(self, include_current: bool = True) -> pd.DataFrame:
        """Return a standard OHLCV DataFrame with DatetimeIndex.

        Args:
            include_current: If True, include the not-yet-closed candle.
        """
        candles = [
            c for c in self._candles
            if include_current or c.closed
        ]
        if not candles:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        rows = [
            {
                "timestamp": pd.to_datetime(c.timestamp, unit="s", utc=True),
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in candles
        ]
        df = pd.DataFrame(rows).set_index("timestamp").sort_index()
        return df
