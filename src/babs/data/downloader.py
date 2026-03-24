"""OHLCV data download via ccxt."""

import logging
from datetime import datetime
from typing import Optional

import ccxt
import pandas as pd

logger = logging.getLogger(__name__)


class OHLCVDownloader:
    """Download OHLCV candle data from exchanges using ccxt."""

    def __init__(self, exchange_id: str = "binance"):
        try:
            exchange_class = getattr(ccxt, exchange_id)
            self.exchange: ccxt.Exchange = exchange_class({"enableRateLimit": True})
        except AttributeError:
            raise ValueError(f"Exchange '{exchange_id}' not supported by ccxt")

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """Fetch OHLCV data and return as a DataFrame.

        Args:
            symbol: Trading pair, e.g. "BTC/USDT".
            timeframe: Candle interval, e.g. "1m", "5m", "1h".
            since: Start time. If None, fetches the most recent candles.
            limit: Maximum number of candles to fetch.

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume.
        """
        since_ms = int(since.timestamp() * 1000) if since else None

        logger.info("Fetching %s %s candles for %s", limit, timeframe, symbol)
        raw = self.exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=limit)

        df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        df = df.astype(float)

        logger.info("Downloaded %d candles", len(df))
        return df

    def fetch_all(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        batch_size: int = 1000,
    ) -> pd.DataFrame:
        """Paginate through history to download a full date range."""
        all_frames = []
        current = start

        while current < end:
            df = self.fetch_ohlcv(symbol, timeframe, since=current, limit=batch_size)
            if df.empty:
                break
            all_frames.append(df)
            current = df.index[-1].to_pydatetime()
            # Avoid infinite loop if we get stuck on the same timestamp
            if len(df) < 2:
                break

        if not all_frames:
            return pd.DataFrame()

        result = pd.concat(all_frames)
        result = result[~result.index.duplicated(keep="first")]
        result = result[result.index <= pd.Timestamp(end)]
        return result.sort_index()
