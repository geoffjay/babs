"""Data storage: CSV and SQLite backends for candle and trade data."""

import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class CSVStorage:
    """Read and write OHLCV data as CSV files."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, symbol: str, timeframe: str) -> Path:
        safe_symbol = symbol.replace("/", "_").replace(" ", "_")
        return self.data_dir / f"{safe_symbol}_{timeframe}.csv"

    def save(self, df: pd.DataFrame, symbol: str, timeframe: str) -> str:
        """Save a DataFrame to CSV. Returns the file path."""
        path = self._path_for(symbol, timeframe)
        df.to_csv(path)
        logger.info("Saved %d rows to %s", len(df), path)
        return str(path)

    def load(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Load a CSV into a DataFrame, or None if it doesn't exist."""
        path = self._path_for(symbol, timeframe)
        if not path.exists():
            logger.warning("No data file at %s", path)
            return None
        df = pd.read_csv(path, index_col="timestamp", parse_dates=True)
        logger.info("Loaded %d rows from %s", len(df), path)
        return df

    def append(self, df: pd.DataFrame, symbol: str, timeframe: str) -> str:
        """Append new rows to an existing CSV, deduplicating by index."""
        existing = self.load(symbol, timeframe)
        if existing is not None:
            combined = pd.concat([existing, df])
            combined = combined[~combined.index.duplicated(keep="last")]
            combined.sort_index(inplace=True)
        else:
            combined = df
        return self.save(combined, symbol, timeframe)


class SQLiteStorage:
    """Read and write OHLCV data to a SQLite database."""

    def __init__(self, db_path: str = "data/market_data.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ohlcv (
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    PRIMARY KEY (symbol, timeframe, timestamp)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    strategy TEXT,
                    symbol TEXT,
                    side TEXT,
                    price REAL,
                    size REAL,
                    pnl REAL,
                    account TEXT
                )
                """
            )

    def save_ohlcv(self, df: pd.DataFrame, symbol: str, timeframe: str) -> int:
        """Upsert OHLCV rows into SQLite. Returns number of rows written."""
        records = df.reset_index()
        records["symbol"] = symbol
        records["timeframe"] = timeframe
        records["timestamp"] = records["timestamp"].astype(str)

        with sqlite3.connect(self.db_path) as conn:
            records.to_sql("ohlcv_staging", conn, if_exists="replace", index=False)
            conn.execute(
                """
                INSERT OR REPLACE INTO ohlcv (symbol, timeframe, timestamp, open, high, low, close, volume)
                SELECT symbol, timeframe, timestamp, open, high, low, close, volume
                FROM ohlcv_staging
                """
            )
            conn.execute("DROP TABLE IF EXISTS ohlcv_staging")

        logger.info("Saved %d OHLCV rows for %s/%s", len(records), symbol, timeframe)
        return len(records)

    def load_ohlcv(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Load OHLCV data from SQLite into a DataFrame."""
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(
                "SELECT timestamp, open, high, low, close, volume FROM ohlcv "
                "WHERE symbol = ? AND timeframe = ? ORDER BY timestamp",
                conn,
                params=(symbol, timeframe),
                parse_dates=["timestamp"],
            )
        if not df.empty:
            df.set_index("timestamp", inplace=True)
        return df

    def log_trade(
        self,
        timestamp: str,
        strategy: str,
        symbol: str,
        side: str,
        price: float,
        size: float,
        pnl: float = 0.0,
        account: str = "",
    ) -> None:
        """Insert a trade record."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO trades (timestamp, strategy, symbol, side, price, size, pnl, account) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (timestamp, strategy, symbol, side, price, size, pnl, account),
            )

    def get_trades(self, strategy: Optional[str] = None) -> pd.DataFrame:
        """Load trade history, optionally filtered by strategy."""
        with sqlite3.connect(self.db_path) as conn:
            if strategy:
                df = pd.read_sql_query(
                    "SELECT * FROM trades WHERE strategy = ? ORDER BY timestamp",
                    conn,
                    params=(strategy,),
                )
            else:
                df = pd.read_sql_query("SELECT * FROM trades ORDER BY timestamp", conn)
        return df
