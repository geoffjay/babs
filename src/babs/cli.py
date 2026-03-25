"""BABS CLI — Polymarket Algorithmic Trading Bot."""

import logging
import sys
from datetime import datetime

import click

STRATEGY_CHOICES = ["macd", "rsi", "cvd", "mm"]


def _setup_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _get_strategy(name: str):
    from babs.strategies.macd_strategy import MACDStrategy
    from babs.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
    from babs.strategies.cvd_strategy import CVDStrategy
    from babs.strategies.market_making_strategy import MarketMakingStrategy

    strategy_map = {
        "macd": MACDStrategy,
        "rsi": RSIMeanReversionStrategy,
        "cvd": CVDStrategy,
        "mm": MarketMakingStrategy,
    }
    return strategy_map[name]()


@click.group()
@click.version_option()
def cli() -> None:
    """BABS — Polymarket Algorithmic Trading Bot.

    An algorithmic trading bot for Polymarket prediction markets,
    built on the RBI methodology (Research → Backtest → Incubate).
    """


@cli.command()
@click.option(
    "--strategy", required=True, type=click.Choice(STRATEGY_CHOICES),
    help="Strategy to backtest.",
)
@click.option("--symbol", default="BTC/USDT", help="Trading pair symbol.")
@click.option("--timeframe", default="1h", help="Candle timeframe.")
@click.option("--start-date", required=True, help="Start date (YYYY-MM-DD).")
@click.option("--end-date", required=True, help="End date (YYYY-MM-DD).")
@click.option("--capital", type=float, default=1000.0, help="Initial capital.")
@click.option("--size", type=float, default=1.0, help="Position size per trade.")
@click.option("--exchange", default="binance", help="Exchange for data download.")
@click.option("--use-cache", is_flag=True, help="Use cached CSV data if available.")
@click.option(
    "--log-level", default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
)
def backtest(
    strategy: str, symbol: str, timeframe: str, start_date: str, end_date: str,
    capital: float, size: float, exchange: str, use_cache: bool, log_level: str,
) -> None:
    """Run a backtest on historical data."""
    from babs.backtesting.engine import BacktestEngine
    from babs.backtesting.metrics import calculate_metrics, print_metrics
    from babs.data.downloader import OHLCVDownloader
    from babs.data.storage import CSVStorage

    _setup_logging(log_level)
    logger = logging.getLogger("babs.backtest")

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    storage = CSVStorage()
    data = None

    if use_cache:
        data = storage.load(symbol, timeframe)
        if data is not None:
            data = data[(data.index >= start) & (data.index <= end)]
            logger.info("Loaded %d cached candles", len(data))

    if data is None or data.empty:
        logger.info("Downloading data from %s...", exchange)
        try:
            downloader = OHLCVDownloader(exchange_id=exchange)
            data = downloader.fetch_all(symbol, timeframe, start, end)
            if data.empty:
                logger.error("No data downloaded for the specified range")
                sys.exit(1)
            storage.save(data, symbol, timeframe)
            logger.info("Downloaded and cached %d candles", len(data))
        except Exception:
            logger.exception("Failed to download data")
            sys.exit(1)

    strat = _get_strategy(strategy)

    logger.info(
        "Running backtest: strategy=%s, %s %s, %s to %s",
        strategy, symbol, timeframe, start_date, end_date,
    )

    engine = BacktestEngine(
        strategy=strat,
        initial_capital=capital,
        position_size=size,
        maker_mode=(strategy == "mm"),
    )
    result = engine.run(data)

    metrics = calculate_metrics(result)
    print_metrics(metrics)

    click.echo(f"Initial capital: ${result.initial_capital:.2f}")
    click.echo(f"Final capital:   ${result.final_capital:.2f}")
    ret = ((result.final_capital - result.initial_capital) / result.initial_capital) * 100
    click.echo(f"Return:          {ret:.2f}%")


@cli.command()
@click.option(
    "--strategy", required=True, type=click.Choice(STRATEGY_CHOICES),
    help="Trading strategy to use.",
)
@click.option("--token-id", required=True, help="Polymarket condition token ID.")
@click.option("--size", type=float, default=1.0, help="Position size in dollars.")
@click.option("--account", default="primary", help="Account name from config.")
@click.option(
    "--log-level", default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
)
def bot(
    strategy: str, token_id: str, size: float, account: str, log_level: str,
) -> None:
    """Launch the trading bot."""
    from babs.config.accounts import get_account_by_name
    from babs.config.settings import Settings
    from babs.data.polymarket_client import PolymarketClient
    from babs.bot.trader import Trader

    _setup_logging(log_level)
    logger = logging.getLogger("babs.bot")

    acct = get_account_by_name(account)
    if acct is None:
        logger.error("Account '%s' not found. Check your .env file.", account)
        sys.exit(1)

    settings = Settings(position_size=size)
    strat = _get_strategy(strategy)

    client = PolymarketClient(
        private_key=acct.private_key,
        funder_address=acct.funder_address,
        host=settings.clob_host,
        chain_id=settings.chain_id,
        signature_type=settings.signature_type,
    )

    logger.info("Connecting to Polymarket...")
    try:
        client.connect()
    except Exception:
        logger.exception("Failed to connect to Polymarket")
        sys.exit(1)

    trader = Trader(
        strategy=strat,
        client=client,
        token_id=token_id,
        settings=settings,
        account_name=account,
    )

    logger.info(
        "Bot starting: strategy=%s, token=%s, size=$%.2f, account=%s",
        strategy, token_id[:16], size, account,
    )

    try:
        trader.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        trader.stop()


@cli.command()
@click.option(
    "--interval", type=int, default=30,
    help="Dashboard refresh interval in seconds.",
)
@click.option(
    "--log-level", default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
)
def monitor(interval: int, log_level: str) -> None:
    """Launch the incubation monitoring dashboard."""
    from babs.incubation.monitor import BotMonitor

    _setup_logging(log_level)
    logger = logging.getLogger("babs.monitor")

    mon = BotMonitor()

    logger.info("Starting monitoring dashboard (refresh every %ds)", interval)
    logger.info("Register bots programmatically via monitor.register(name, tracker)")

    try:
        mon.run_loop(interval_seconds=interval)
    except KeyboardInterrupt:
        logger.info("Monitor stopped")
