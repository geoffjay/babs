#!/usr/bin/env python3
"""Entry point: launch the trading bot."""

import argparse
import logging
import sys

from config.accounts import get_account_by_name
from config.settings import Settings
from data.polymarket_client import PolymarketClient
from bot.trader import Trader
from strategies.macd_strategy import MACDStrategy
from strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from strategies.cvd_strategy import CVDStrategy

STRATEGY_MAP = {
    "macd": MACDStrategy,
    "rsi": RSIMeanReversionStrategy,
    "cvd": CVDStrategy,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Polymarket RBI Trading Bot")
    parser.add_argument(
        "--strategy",
        choices=list(STRATEGY_MAP.keys()),
        required=True,
        help="Trading strategy to use",
    )
    parser.add_argument(
        "--token-id",
        required=True,
        help="Polymarket condition token ID to trade",
    )
    parser.add_argument(
        "--size",
        type=float,
        default=1.0,
        help="Position size in dollars (default: 1)",
    )
    parser.add_argument(
        "--account",
        default="primary",
        help="Account name from config (default: primary)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("run_bot")

    # Load account
    account = get_account_by_name(args.account)
    if account is None:
        logger.error("Account '%s' not found. Check your .env file.", args.account)
        sys.exit(1)

    # Build settings
    settings = Settings(position_size=args.size)

    # Initialize strategy
    strategy_cls = STRATEGY_MAP[args.strategy]
    strategy = strategy_cls()

    # Initialize Polymarket client
    client = PolymarketClient(
        private_key=account.private_key,
        funder_address=account.funder_address,
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

    # Create and run trader
    trader = Trader(
        strategy=strategy,
        client=client,
        token_id=args.token_id,
        settings=settings,
        account_name=args.account,
    )

    logger.info(
        "Bot starting: strategy=%s, token=%s, size=$%.2f, account=%s",
        args.strategy, args.token_id[:16], args.size, args.account,
    )

    try:
        trader.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        trader.stop()


if __name__ == "__main__":
    main()
