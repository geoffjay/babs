#!/usr/bin/env python3
"""Entry point: incubation monitoring dashboard."""

import argparse
import logging

from incubation.monitor import BotMonitor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bot Incubation Monitor")
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Dashboard refresh interval in seconds (default: 30)",
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
    logger = logging.getLogger("run_monitor")

    monitor = BotMonitor()

    # In a production setup, this would connect to running bot processes
    # (e.g., via shared memory, a message queue, or a database) to collect
    # their PositionTracker instances. For now, it starts the dashboard loop
    # which will display data as bots are registered.

    logger.info("Starting monitoring dashboard (refresh every %ds)", args.interval)
    logger.info("Register bots programmatically via monitor.register(name, tracker)")

    try:
        monitor.run_loop(interval_seconds=args.interval)
    except KeyboardInterrupt:
        logger.info("Monitor stopped")


if __name__ == "__main__":
    main()
