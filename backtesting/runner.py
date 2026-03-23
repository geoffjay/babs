"""Parallel backtest runner using multiprocessing."""

import logging
from dataclasses import dataclass
from multiprocessing import Pool, cpu_count
from typing import Dict, List, Optional, Tuple

import pandas as pd

from backtesting.engine import BacktestEngine, BacktestResult
from backtesting.metrics import PerformanceMetrics, calculate_metrics, print_metrics
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


@dataclass
class BacktestJob:
    strategy: BaseStrategy
    data: pd.DataFrame
    initial_capital: float = 1000.0
    position_size: float = 1.0
    label: str = ""


def _run_single(job: BacktestJob) -> Tuple[str, BacktestResult, PerformanceMetrics]:
    """Execute a single backtest job (designed to run in a worker process)."""
    engine = BacktestEngine(
        strategy=job.strategy,
        initial_capital=job.initial_capital,
        position_size=job.position_size,
    )
    result = engine.run(job.data)
    metrics = calculate_metrics(result)
    return job.label, result, metrics


class BacktestRunner:
    """Run multiple backtests in parallel and aggregate results."""

    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or max(1, cpu_count() - 1)

    def run_parallel(
        self, jobs: List[BacktestJob]
    ) -> Dict[str, Tuple[BacktestResult, PerformanceMetrics]]:
        """Run a list of backtest jobs in parallel.

        Args:
            jobs: List of BacktestJob instances.

        Returns:
            Dictionary mapping job label to (BacktestResult, PerformanceMetrics).
        """
        if not jobs:
            return {}

        logger.info("Running %d backtests across %d workers", len(jobs), self.max_workers)

        results: Dict[str, Tuple[BacktestResult, PerformanceMetrics]] = {}

        # multiprocessing.Pool requires picklable arguments; strategies and
        # DataFrames are generally picklable.  Fall back to sequential execution
        # if the pool fails (e.g., in environments that restrict forking).
        try:
            with Pool(processes=self.max_workers) as pool:
                outputs = pool.map(_run_single, jobs)
            for label, result, metrics in outputs:
                results[label] = (result, metrics)
        except Exception as e:
            logger.warning("Parallel execution failed (%s), falling back to sequential", e)
            for job in jobs:
                label, result, metrics = _run_single(job)
                results[label] = (result, metrics)

        return results

    def run_sequential(
        self, jobs: List[BacktestJob]
    ) -> Dict[str, Tuple[BacktestResult, PerformanceMetrics]]:
        """Run jobs sequentially (useful for debugging)."""
        results: Dict[str, Tuple[BacktestResult, PerformanceMetrics]] = {}
        for job in jobs:
            label, result, metrics = _run_single(job)
            results[label] = (result, metrics)
        return results

    @staticmethod
    def print_summary(results: Dict[str, Tuple[BacktestResult, PerformanceMetrics]]) -> None:
        """Print a summary table of all backtest results."""
        print("\n" + "=" * 80)
        print("                     BACKTEST COMPARISON SUMMARY")
        print("=" * 80)
        header = f"{'Label':<20} {'Trades':>7} {'Win%':>7} {'PF':>7} {'Sharpe':>8} {'MaxDD%':>8} {'PnL':>10}"
        print(header)
        print("-" * 80)

        for label, (result, metrics) in sorted(results.items()):
            row = (
                f"{label:<20} "
                f"{metrics.total_trades:>7} "
                f"{metrics.win_rate:>6.1%} "
                f"{metrics.profit_factor:>7.2f} "
                f"{metrics.sharpe_ratio:>8.2f} "
                f"{metrics.max_drawdown_pct:>7.2%} "
                f"{metrics.total_pnl:>10.2f}"
            )
            print(row)

        print("=" * 80 + "\n")
