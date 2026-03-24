"""Backtest performance metrics."""

import logging
from dataclasses import dataclass
from typing import List

import numpy as np

from babs.backtesting.engine import BacktestResult, Trade

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    total_pnl: float
    avg_pnl_per_trade: float
    avg_winner: float
    avg_loser: float
    best_trade: float
    worst_trade: float


def calculate_metrics(
    result: BacktestResult,
    risk_free_rate: float = 0.0,
    periods_per_year: float = 252.0,
) -> PerformanceMetrics:
    """Compute comprehensive performance metrics from a backtest result.

    Args:
        result: A completed BacktestResult.
        risk_free_rate: Annualized risk-free rate for Sharpe calculation.
        periods_per_year: Number of trading periods per year.

    Returns:
        PerformanceMetrics dataclass.
    """
    trades: List[Trade] = result.trades
    equity = result.equity_curve

    total_trades = len(trades)
    if total_trades == 0:
        return PerformanceMetrics(
            total_trades=0, winning_trades=0, losing_trades=0,
            win_rate=0.0, profit_factor=0.0, sharpe_ratio=0.0,
            max_drawdown=0.0, max_drawdown_pct=0.0, total_pnl=0.0,
            avg_pnl_per_trade=0.0, avg_winner=0.0, avg_loser=0.0,
            best_trade=0.0, worst_trade=0.0,
        )

    pnls = [t.pnl for t in trades]
    winners = [p for p in pnls if p > 0]
    losers = [p for p in pnls if p <= 0]

    total_pnl = sum(pnls)
    winning_trades = len(winners)
    losing_trades = len(losers)
    win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

    gross_profit = sum(winners) if winners else 0.0
    gross_loss = abs(sum(losers)) if losers else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0

    avg_pnl_per_trade = total_pnl / total_trades
    avg_winner = np.mean(winners) if winners else 0.0
    avg_loser = np.mean(losers) if losers else 0.0
    best_trade = max(pnls)
    worst_trade = min(pnls)

    # Sharpe ratio from equity curve returns
    sharpe_ratio = _compute_sharpe(equity, risk_free_rate, periods_per_year)

    # Maximum drawdown
    max_dd, max_dd_pct = _compute_max_drawdown(equity)

    return PerformanceMetrics(
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=win_rate,
        profit_factor=profit_factor,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_dd,
        max_drawdown_pct=max_dd_pct,
        total_pnl=total_pnl,
        avg_pnl_per_trade=avg_pnl_per_trade,
        avg_winner=float(avg_winner),
        avg_loser=float(avg_loser),
        best_trade=best_trade,
        worst_trade=worst_trade,
    )


def _compute_sharpe(
    equity: List[float],
    risk_free_rate: float = 0.0,
    periods_per_year: float = 252.0,
) -> float:
    """Annualized Sharpe ratio from an equity curve."""
    if len(equity) < 2:
        return 0.0

    arr = np.array(equity)
    returns = np.diff(arr) / arr[:-1]
    returns = returns[np.isfinite(returns)]

    if len(returns) == 0 or np.std(returns) == 0:
        return 0.0

    excess_return = np.mean(returns) - (risk_free_rate / periods_per_year)
    return float(excess_return / np.std(returns) * np.sqrt(periods_per_year))


def _compute_max_drawdown(equity: List[float]) -> tuple:
    """Compute maximum drawdown in absolute and percentage terms."""
    if len(equity) < 2:
        return 0.0, 0.0

    arr = np.array(equity)
    peak = np.maximum.accumulate(arr)
    drawdown = peak - arr
    max_dd = float(np.max(drawdown))

    dd_pct = drawdown / np.where(peak > 0, peak, 1.0)
    max_dd_pct = float(np.max(dd_pct))

    return max_dd, max_dd_pct


def print_metrics(metrics: PerformanceMetrics) -> None:
    """Pretty-print performance metrics to the console."""
    print("\n" + "=" * 50)
    print("       BACKTEST PERFORMANCE METRICS")
    print("=" * 50)
    print(f"  Total Trades:      {metrics.total_trades}")
    print(f"  Winning Trades:    {metrics.winning_trades}")
    print(f"  Losing Trades:     {metrics.losing_trades}")
    print(f"  Win Rate:          {metrics.win_rate:.2%}")
    print(f"  Profit Factor:     {metrics.profit_factor:.2f}")
    print(f"  Sharpe Ratio:      {metrics.sharpe_ratio:.2f}")
    print(f"  Max Drawdown:      ${metrics.max_drawdown:.2f} ({metrics.max_drawdown_pct:.2%})")
    print(f"  Total PnL:         ${metrics.total_pnl:.2f}")
    print(f"  Avg PnL/Trade:     ${metrics.avg_pnl_per_trade:.4f}")
    print(f"  Avg Winner:        ${metrics.avg_winner:.4f}")
    print(f"  Avg Loser:         ${metrics.avg_loser:.4f}")
    print(f"  Best Trade:        ${metrics.best_trade:.4f}")
    print(f"  Worst Trade:       ${metrics.worst_trade:.4f}")
    print("=" * 50 + "\n")
