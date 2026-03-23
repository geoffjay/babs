#!/usr/bin/env python3
"""Entry point: run a backtest on historical data."""

import argparse
import logging
import sys
from datetime import datetime

from backtesting.engine import BacktestEngine
from backtesting.metrics import calculate_metrics, print_metrics
from data.downloader import OHLCVDownloader
from data.storage import CSVStorage
from strategies.macd_strategy import MACDStrategy
from strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from strategies.cvd_strategy import CVDStrategy

STRATEGY_MAP = {
    "macd": MACDStrategy,
    "rsi": RSIMeanReversionStrategy,
    "cvd": CVDStrategy,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a backtest")
    parser.add_argument(
        "--strategy",
        choices=list(STRATEGY_MAP.keys()),
        required=True,
        help="Strategy to backtest",
    )
    parser.add_argument(
        "--symbol",
        default="BTC/USDT",
        help="Trading pair symbol (default: BTC/USDT)",
    )
    parser.add_argument(
        "--timeframe",
        default="1h",
        help="Candle timeframe (default: 1h)",
    )
    parser.add_argument(
        "--start-date",
        required=True,
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        required=True,
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=1000.0,
        help="Initial capital (default: 1000)",
    )
    parser.add_argument(
        "--size",
        type=float,
        default=1.0,
        help="Position size (default: 1)",
    )
    parser.add_argument(
        "--exchange",
        default="binance",
        help="Exchange for data download (default: binance)",
    )
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="Use cached CSV data if available",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("run_backtest")

    start = datetime.strptime(args.start_date, "%Y-%m-%d")
    end = datetime.strptime(args.end_date, "%Y-%m-%d")

    # Load or download data
    storage = CSVStorage()
    data = None

    if args.use_cache:
        data = storage.load(args.symbol, args.timeframe)
        if data is not None:
            # Filter to date range
            data = data[(data.index >= start) & (data.index <= end)]
            logger.info("Loaded %d cached candles", len(data))

    if data is None or data.empty:
        logger.info("Downloading data from %s...", args.exchange)
        try:
            downloader = OHLCVDownloader(exchange_id=args.exchange)
            data = downloader.fetch_all(args.symbol, args.timeframe, start, end)
            if data.empty:
                logger.error("No data downloaded for the specified range")
                sys.exit(1)
            storage.save(data, args.symbol, args.timeframe)
            logger.info("Downloaded and cached %d candles", len(data))
        except Exception:
            logger.exception("Failed to download data")
            sys.exit(1)

    # Initialize strategy
    strategy_cls = STRATEGY_MAP[args.strategy]
    strategy = strategy_cls()

    # Run backtest
    logger.info(
        "Running backtest: strategy=%s, %s %s, %s to %s",
        args.strategy, args.symbol, args.timeframe, args.start_date, args.end_date,
    )

    engine = BacktestEngine(
        strategy=strategy,
        initial_capital=args.capital,
        position_size=args.size,
    )
    result = engine.run(data)

    # Calculate and display metrics
    metrics = calculate_metrics(result)
    print_metrics(metrics)

    print(f"Initial capital: ${result.initial_capital:.2f}")
    print(f"Final capital:   ${result.final_capital:.2f}")
    print(f"Return:          {((result.final_capital - result.initial_capital) / result.initial_capital) * 100:.2f}%")


if __name__ == "__main__":
    main()
