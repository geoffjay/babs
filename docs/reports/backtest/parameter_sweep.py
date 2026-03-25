"""Comprehensive backtest parameter sweep across strategies, symbols, and timeframes."""

import itertools
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from babs.backtesting.engine import BacktestEngine
from babs.backtesting.metrics import calculate_metrics
from babs.data.downloader import OHLCVDownloader
from babs.data.storage import CSVStorage
from babs.strategies.cvd_strategy import CVDStrategy
from babs.strategies.macd_strategy import MACDStrategy
from babs.strategies.rsi_mean_reversion import RSIMeanReversionStrategy

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("parameter_sweep")
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "ohlcv"
OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_CSV = OUTPUT_DIR / "sweep_results.csv"

SYMBOLS = ["BTC/USDT", "ETH/USDT"]
TIMEFRAMES = ["1h", "4h"]  # skip 15m — too slow to sweep, already proven bad
START = datetime(2025, 1, 1)
END = datetime(2025, 3, 1)

INITIAL_CAPITAL = 1000.0
POSITION_SIZE = 0.01

STOP_LOSSES = [0.03, 0.05, 0.07]
TAKE_PROFITS = [0.05, 0.10, 0.15]

# Periods-per-year lookup for Sharpe ratio calculation
PERIODS_PER_YEAR = {
    "15m": 365.25 * 24 * 4,  # ~35064
    "1h": 365.25 * 24,       # ~8766
    "4h": 365.25 * 6,        # ~2191
}

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def download_data(
    symbols: list[str],
    timeframes: list[str],
    start: datetime,
    end: datetime,
) -> dict[tuple[str, str], pd.DataFrame]:
    """Download (or load from cache) OHLCV data for each symbol/timeframe pair."""
    storage = CSVStorage(data_dir=str(DATA_DIR))
    downloader = OHLCVDownloader(exchange_id="binance")
    data: dict[tuple[str, str], pd.DataFrame] = {}

    for symbol in symbols:
        for tf in timeframes:
            key = (symbol, tf)
            cached = storage.load(symbol, tf)
            if cached is not None and len(cached) > 0:
                logger.info("Using cached data for %s %s (%d rows)", symbol, tf, len(cached))
                data[key] = cached
                continue

            logger.info("Downloading %s %s from %s to %s ...", symbol, tf, start, end)
            try:
                df = downloader.fetch_all(symbol, tf, start, end)
                if df.empty:
                    logger.warning("No data returned for %s %s", symbol, tf)
                    continue
                storage.save(df, symbol, tf)
                data[key] = df
                logger.info("Downloaded %d rows for %s %s", len(df), symbol, tf)
            except Exception as exc:
                logger.error("Failed to download %s %s: %s", symbol, tf, exc)

    return data


# ---------------------------------------------------------------------------
# Parameter configurations
# ---------------------------------------------------------------------------

def build_macd_configs() -> list[dict]:
    """Build MACD parameter grid — focused on slower, more viable params."""
    configs = []
    for fast, slow, signal, sl, tp in itertools.product(
        [8, 12], [21, 26, 34], [5, 9], STOP_LOSSES, TAKE_PROFITS,
    ):
        if fast >= slow:
            continue
        configs.append({
            "strategy_name": "MACD",
            "params": {"fast": fast, "slow": slow, "signal": signal,
                       "stop_loss_pct": sl, "take_profit_pct": tp},
        })
    return configs


def build_rsi_configs() -> list[dict]:
    """Build RSI parameter grid."""
    configs = []
    for period, oversold, overbought, sl, tp in itertools.product(
        [7, 14, 21], [20, 30], [70, 80], STOP_LOSSES, TAKE_PROFITS,
    ):
        configs.append({
            "strategy_name": "RSI",
            "params": {"period": period, "oversold": oversold, "overbought": overbought,
                       "stop_loss_pct": sl, "take_profit_pct": tp},
        })
    return configs


def build_cvd_configs() -> list[dict]:
    """Build CVD parameter grid."""
    configs = []
    for lookback, div_thresh, sl, tp in itertools.product(
        [10, 15, 20, 30], [0.005, 0.01, 0.02, 0.03], STOP_LOSSES, TAKE_PROFITS,
    ):
        configs.append({
            "strategy_name": "CVD",
            "params": {"lookback": lookback, "divergence_threshold": div_thresh,
                       "stop_loss_pct": sl, "take_profit_pct": tp},
        })
    return configs


def make_strategy(cfg: dict):
    """Instantiate a strategy from a config dict."""
    name = cfg["strategy_name"]
    p = cfg["params"]
    if name == "MACD":
        return MACDStrategy(
            fast=p["fast"], slow=p["slow"], signal=p["signal"],
            stop_loss_pct=p["stop_loss_pct"], take_profit_pct=p["take_profit_pct"],
        )
    elif name == "RSI":
        return RSIMeanReversionStrategy(
            period=p["period"], oversold=p["oversold"], overbought=p["overbought"],
            stop_loss_pct=p["stop_loss_pct"], take_profit_pct=p["take_profit_pct"],
        )
    elif name == "CVD":
        return CVDStrategy(
            lookback=p["lookback"], divergence_threshold=p["divergence_threshold"],
            stop_loss_pct=p["stop_loss_pct"], take_profit_pct=p["take_profit_pct"],
        )
    else:
        raise ValueError(f"Unknown strategy: {name}")


# ---------------------------------------------------------------------------
# Main sweep
# ---------------------------------------------------------------------------

def run_sweep(data: dict[tuple[str, str], pd.DataFrame]) -> pd.DataFrame:
    """Execute the full parameter sweep and return results as a DataFrame."""
    all_configs = build_macd_configs() + build_rsi_configs() + build_cvd_configs()

    # Sort datasets by row count (ascending) so fast timeframes finish first
    sorted_keys = sorted(data.keys(), key=lambda k: len(data[k]))
    total_combos = len(all_configs) * len(data)
    logger.info("Total configurations to test: %d strategies x %d datasets = %d runs",
                len(all_configs), len(data), total_combos)

    rows: list[dict] = []
    completed = 0
    t0 = time.time()

    for (symbol, tf) in sorted_keys:
        df = data[(symbol, tf)]
        logger.info("Starting dataset: %s %s (%d rows, %d configs)",
                    symbol, tf, len(df), len(all_configs))
        periods_yr = PERIODS_PER_YEAR.get(tf, 252.0)
        dataset_t0 = time.time()
        for cfg in all_configs:
            completed += 1
            if completed % 50 == 0 or completed == 1:
                elapsed = time.time() - t0
                rate = completed / elapsed if elapsed > 0 else 0
                eta = (total_combos - completed) / rate if rate > 0 else 0
                logger.info(
                    "Progress: %d / %d (%.1f%%) | %.1f runs/s | ETA %.0fs",
                    completed, total_combos, 100 * completed / total_combos, rate, eta,
                )

            try:
                strategy = make_strategy(cfg)
                engine = BacktestEngine(
                    strategy=strategy,
                    initial_capital=INITIAL_CAPITAL,
                    position_size=POSITION_SIZE,
                )
                result = engine.run(df)
                metrics = calculate_metrics(result, periods_per_year=periods_yr)

                return_pct = ((result.final_capital - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100

                rows.append({
                    "strategy": cfg["strategy_name"],
                    "symbol": symbol,
                    "timeframe": tf,
                    "params": str(cfg["params"]),
                    "trades": metrics.total_trades,
                    "win_rate": round(metrics.win_rate, 4),
                    "sharpe": round(metrics.sharpe_ratio, 4),
                    "max_drawdown_pct": round(metrics.max_drawdown_pct, 4),
                    "return_pct": round(return_pct, 4),
                    "profit_factor": round(metrics.profit_factor, 4),
                    "avg_pnl": round(metrics.avg_pnl_per_trade, 6),
                })
            except Exception as exc:
                logger.warning(
                    "Error running %s on %s/%s with %s: %s",
                    cfg["strategy_name"], symbol, tf, cfg["params"], exc,
                )
        dataset_elapsed = time.time() - dataset_t0
        logger.info("Finished %s %s in %.1fs", symbol, tf, dataset_elapsed)
        # Save partial results after each dataset
        partial_df = pd.DataFrame(rows)
        partial_df.to_csv(OUTPUT_CSV, index=False)
        logger.info("Saved %d partial results to %s", len(rows), OUTPUT_CSV)

    elapsed = time.time() - t0
    logger.info("Sweep complete: %d results in %.1fs", len(rows), elapsed)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_top_bottom(df: pd.DataFrame) -> None:
    """Print the top 20 and bottom 10 configurations by Sharpe ratio."""
    # Filter to configs with at least 1 trade
    active = df[df["trades"] > 0].copy()
    if active.empty:
        print("\nNo configurations produced any trades.")
        return

    sorted_df = active.sort_values("sharpe", ascending=False)

    print("\n" + "=" * 120)
    print("  TOP 20 CONFIGURATIONS BY SHARPE RATIO")
    print("=" * 120)
    print(sorted_df.head(20).to_string(index=False))

    print("\n" + "=" * 120)
    print("  BOTTOM 10 CONFIGURATIONS BY SHARPE RATIO")
    print("=" * 120)
    print(sorted_df.tail(10).to_string(index=False))


def print_summary(df: pd.DataFrame) -> None:
    """Print summary analysis by strategy."""
    print("\n" + "=" * 80)
    print("  SUMMARY BY STRATEGY")
    print("=" * 80)

    for strat_name in sorted(df["strategy"].unique()):
        subset = df[df["strategy"] == strat_name]
        active = subset[subset["trades"] > 0]
        profitable = active[active["return_pct"] > 0]
        unprofitable = active[active["return_pct"] <= 0]

        print(f"\n--- {strat_name} ---")
        print(f"  Total configs tested:   {len(subset)}")
        print(f"  Configs with trades:    {len(active)}")
        print(f"  Profitable configs:     {len(profitable)}")
        print(f"  Unprofitable configs:   {len(unprofitable)}")
        if len(active) > 0:
            print(f"  Profitability rate:     {len(profitable) / len(active):.1%}")
            print(f"  Avg Sharpe (active):    {active['sharpe'].mean():.4f}")
            print(f"  Avg return % (active):  {active['return_pct'].mean():.4f}%")
            print(f"  Best Sharpe:            {active['sharpe'].max():.4f}")
            print(f"  Worst Sharpe:           {active['sharpe'].min():.4f}")
            print(f"  Median trades:          {active['trades'].median():.0f}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("Starting parameter sweep backtest")
    logger.info("Symbols: %s | Timeframes: %s", SYMBOLS, TIMEFRAMES)
    logger.info("Date range: %s to %s", START, END)

    # Step 1: download / load data
    data = download_data(SYMBOLS, TIMEFRAMES, START, END)
    if not data:
        logger.error("No data available. Exiting.")
        sys.exit(1)

    logger.info("Loaded data for %d symbol/timeframe pairs", len(data))
    for (sym, tf), df in data.items():
        logger.info("  %s %s: %d rows", sym, tf, len(df))

    # Step 2-4: run the sweep
    results_df = run_sweep(data)
    if results_df.empty:
        logger.error("No results produced. Exiting.")
        sys.exit(1)

    # Step 5: save to CSV
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(OUTPUT_CSV, index=False)
    logger.info("Results saved to %s", OUTPUT_CSV)

    # Step 6-7: print reports
    print_top_bottom(results_df)
    print_summary(results_df)

    print(f"\nResults written to: {OUTPUT_CSV}")
    print(f"Total configurations evaluated: {len(results_df)}")


if __name__ == "__main__":
    main()
