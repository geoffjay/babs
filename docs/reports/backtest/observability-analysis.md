# BABS Observability & Instrumentation Analysis

**Date:** 2026-03-24
**Scope:** All Python source files under `src/babs/`

---

## 1. Current Logging State

### 1.1 Logger Setup

All logging flows through Python's stdlib `logging` module, configured once
in `cli.py`:

```python
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
```

Every module creates its own logger with `logging.getLogger(__name__)`.
This is good practice. However, the format is a plain string -- not structured
(no JSON, no key=value fields) -- which makes automated parsing impossible.

### 1.2 Complete Inventory of Log Calls

| File | Level | Message / Pattern | What It Captures |
|------|-------|-------------------|------------------|
| **cli.py** | INFO | `"Loaded %d cached candles"` | Row count only |
| **cli.py** | INFO | `"Downloading data from %s..."` | Exchange name |
| **cli.py** | ERROR | `"No data downloaded for the specified range"` | No context on range or symbol |
| **cli.py** | INFO | `"Downloaded and cached %d candles"` | Row count |
| **cli.py** | EXCEPTION | `"Failed to download data"` | Full traceback |
| **cli.py** | INFO | `"Running backtest: strategy=%s, %s %s, %s to %s"` | Strategy, symbol, timeframe, dates |
| **cli.py** | INFO | `"Connecting to Polymarket..."` | Nothing useful |
| **cli.py** | INFO | `"Bot starting: strategy=%s, token=%s, size=$%.2f, account=%s"` | Good summary |
| **cli.py** | INFO | `"Shutting down..."` | No context |
| **cli.py** | INFO | `"Starting monitoring dashboard (refresh every %ds)"` | Interval |
| **engine.py** | DEBUG | `"Closed %s @ %.4f -> %.4f, PnL=%.4f"` | Side, prices, PnL |
| **engine.py** | DEBUG | `"Opened %s @ %.4f, size=%.4f"` | Side, price, size |
| **engine.py** | INFO | `"Backtest complete: %d trades, final capital=%.2f (%.2f%%)"` | Summary only |
| **runner.py** | INFO | `"Running %d backtests across %d workers"` | Job count, worker count |
| **runner.py** | WARNING | `"Parallel execution failed (%s), falling back to sequential"` | Exception message |
| **macd_strategy.py** | INFO | `"MACD bullish/bearish crossover detected (hist: ...)"` | Histogram values |
| **macd_strategy.py** | INFO | `"MACD exit: stop-loss/take-profit/reverse crossover"` | PnL % or direction |
| **rsi_mean_reversion.py** | INFO | `"RSI oversold/overbought signal: RSI=%.2f"` | RSI value vs threshold |
| **rsi_mean_reversion.py** | INFO | `"RSI exit: stop-loss/take-profit/RSI reverted/VWAP"` | RSI or price vs VWAP |
| **cvd_strategy.py** | INFO | `"CVD bullish/bearish divergence: price_change=..., cvd_norm=..."` | Price change, CVD norm |
| **cvd_strategy.py** | INFO | `"CVD exit: stop-loss/take-profit/divergence resolved"` | PnL % or state |
| **risk_manager.py** | WARNING | `"RISK BLOCK: max drawdown/positions/daily loss"` | Current vs limit |
| **risk_manager.py** | INFO | `"Order size reduced: %.2f -> %.2f"` | Old/new size, max notional |
| **trader.py** | INFO | `"Exit signal for %s"` | Token ID prefix |
| **trader.py** | INFO | `"Trade closed: PnL=%.4f"` | PnL only |
| **trader.py** | DEBUG | `"Risk manager blocked new trade"` | No reason why |
| **trader.py** | INFO | `"Entry signal: %s %s @ %.4f x %.2f"` | Side, token, price, size |
| **trader.py** | INFO | `"Starting trader: strategy=%s, token=%s, account=%s"` | Summary |
| **trader.py** | DEBUG | `"No data available, skipping tick"` | Nothing |
| **trader.py** | EXCEPTION | `"Error in trading loop"` | Full traceback |
| **trader.py** | INFO | `"Trader stopped"` | Nothing |
| **order_manager.py** | DEBUG | `"Cancel verification attempt %d/%d"` | Attempt, remaining count |
| **order_manager.py** | WARNING | `"Cancel verification failed"` | Remaining count, retries |
| **order_manager.py** | INFO | `"Cancelling existing orders"` | Market/token IDs |
| **order_manager.py** | WARNING | `"Duplicate order rejected"` | Side, token, price, size |
| **order_manager.py** | INFO | `"Order placed: id=%s %s @ %.4f x %.2f"` | Order ID, side, price, size |
| **order_manager.py** | ERROR | `"Order failed: %s"` | Error message |
| **order_manager.py** | INFO | `"Order %s no longer on exchange, removed"` | Order ID |
| **order_manager.py** | ERROR | `"Aborting order placement: could not verify cancellation"` | Token prefix |
| **position_tracker.py** | INFO | `"Position opened/closed"` | Side, token, price, size, PnL |
| **position_tracker.py** | WARNING | `"No open position found for token"` | Token, account |
| **polymarket_client.py** | INFO | `"Connected to Polymarket CLOB"` | Host |
| **polymarket_client.py** | INFO | `"Placed %s limit order"` | Side, token, price, size, order ID |
| **polymarket_client.py** | ERROR | `"Failed to place/cancel/fetch orders/book/history"` | Exception message |
| **polymarket_client.py** | INFO | `"Cancelled all open orders"` | Market/token |
| **downloader.py** | INFO | `"Fetching %s %s candles for %s"` | Limit, timeframe, symbol |
| **downloader.py** | INFO | `"Downloaded %d candles"` | Row count |
| **storage.py** | INFO | `"Saved %d rows to %s"` | Row count, path |
| **storage.py** | INFO | `"Loaded %d rows from %s"` | Row count, path |
| **storage.py** | WARNING | `"No data file at %s"` | Path |
| **storage.py** | INFO | `"Saved %d OHLCV rows for %s/%s"` | Row count, symbol, timeframe |
| **incubation/monitor.py** | INFO | `"Registered bot '%s'"` | Bot name |
| **incubation/monitor.py** | INFO | `"Starting monitoring loop"` | Interval |
| **incubation/scaler.py** | DEBUG | `"Not enough trades for scaling"` | Trade count |
| **incubation/scaler.py** | INFO | `"Scaling UP/DOWN"` | Win rate, PF, old/new size |
| **incubation/scaler.py** | INFO | `"Position scaler reset"` | Base size |
| **incubation/logger.py** | INFO | `"Created trade log at %s"` | File path |
| **incubation/logger.py** | DEBUG | `"Logged trade: %s %s @ %.4f"` | Side, token, price |
| **incubation/logger.py** | EXCEPTION | `"Failed to write trade log"` | Full traceback |

### 1.3 What Is Missing

**Backtest blind spots:**
- **No progress indication.** `engine.py` iterates silently over potentially
  tens of thousands of bars. A 30-second MACD 5m run produces zero output
  until it finishes.
- **No per-bar indicator values.** Strategies log only when a signal fires.
  The vast majority of HOLD decisions are completely silent -- you cannot
  reconstruct *why* nothing happened on a given bar.
- **No trade-level structured data.** Trade open/close events use `logger.debug`,
  which is invisible at the default INFO level. Even at DEBUG, the data is
  embedded in format strings, not structured fields.
- **No equity curve streaming.** The equity curve is computed internally but
  never surfaced until the full run completes.

**Live trading blind spots:**
- **No API latency tracking.** Every `PolymarketClient` method does a
  network call but records neither duration nor response size.
- **No data freshness metric.** The `Trader` has no awareness of how stale
  its latest candle is.
- **Risk manager decisions are opaque from the caller's perspective.**
  `trader.py` logs "Risk manager blocked new trade" at DEBUG with no
  indication of *which* limit was hit; the detailed reason is logged
  separately inside `risk_manager.py` at WARNING.
- **Order lifecycle is fragmented.** The placed/cancelled/filled state
  transitions are spread across `order_manager.py`, `polymarket_client.py`,
  and `trader.py` with no correlation ID.
- **No heartbeat.** There is no periodic "I'm alive" log from the trading loop.

**Structural issues:**
- All logs are unstructured strings. Impossible to filter/aggregate in any
  log management tool.
- No request/trace IDs. Cannot correlate a signal event to the order it
  produced.
- No duration measurements anywhere.
- No metrics (counters, gauges, histograms) -- only text logs.

---

## 2. Instrumentation Plan

### 2.1 Backtest Monitoring

#### 2.1.1 Progress Reporting

The backtest engine loop in `engine.py` should emit progress at regular
intervals. The approach: a callback protocol that the engine invokes, with
a default no-op implementation and an opt-in rich progress reporter.

```python
# src/babs/backtesting/engine.py -- additions

import time
from typing import Callable, Optional, Protocol

class ProgressCallback(Protocol):
    def __call__(
        self,
        bar: int,
        total_bars: int,
        elapsed_seconds: float,
        trades_so_far: int,
        current_equity: float,
    ) -> None: ...

def _default_progress(bar, total_bars, elapsed, trades, equity):
    """No-op progress callback."""
    pass

def _log_progress(bar, total_bars, elapsed, trades, equity):
    """Periodic log-based progress."""
    pct = bar / total_bars * 100
    bars_per_sec = bar / elapsed if elapsed > 0 else 0
    eta = (total_bars - bar) / bars_per_sec if bars_per_sec > 0 else 0
    logger.info(
        "Backtest progress: %d/%d bars (%.1f%%) | %.0f bars/sec | "
        "ETA %.1fs | %d trades | equity $%.2f",
        bar, total_bars, pct, bars_per_sec, eta, trades, equity,
    )
```

Inside `BacktestEngine.run()`:

```python
def run(
    self,
    data: pd.DataFrame,
    progress_callback: Optional[ProgressCallback] = None,
    progress_interval: int = 2000,  # emit every N bars
) -> BacktestResult:
    callback = progress_callback or _log_progress
    t0 = time.monotonic()
    total_bars = len(data) - min_bars

    for i in range(min_bars, len(data)):
        bar_num = i - min_bars + 1

        # ... existing logic ...

        if bar_num % progress_interval == 0 or bar_num == total_bars:
            callback(
                bar=bar_num,
                total_bars=total_bars,
                elapsed_seconds=time.monotonic() - t0,
                trades_so_far=len(result.trades),
                current_equity=capital + unrealized,
            )
```

For the CLI, wire it up with a Rich progress bar:

```python
# In cli.py backtest command, opt-in with --progress flag:
from rich.progress import Progress

with Progress() as progress:
    task = progress.add_task("Backtesting...", total=len(data))

    def update_progress(bar, total_bars, elapsed, trades, equity):
        progress.update(task, completed=bar, description=(
            f"Backtesting... {trades} trades, ${equity:.0f}"
        ))

    result = engine.run(data, progress_callback=update_progress, progress_interval=100)
```

#### 2.1.2 Per-Trade Structured Logging

Replace the current `logger.debug` calls in `engine.py` with structured
event dicts. This enables both human-readable logs and machine-parseable
trade journals.

```python
# src/babs/backtesting/engine.py -- trade events

def _log_trade_open(self, trade_num: int, side: str, price: float,
                     size: float, timestamp: pd.Timestamp, capital: float):
    logger.info(
        "trade.open",
        extra={
            "event": "trade.open",
            "trade_num": trade_num,
            "side": side,
            "entry_price": price,
            "size": size,
            "timestamp": str(timestamp),
            "capital_before": capital,
        },
    )

def _log_trade_close(self, trade_num: int, trade: Trade, capital: float):
    logger.info(
        "trade.close",
        extra={
            "event": "trade.close",
            "trade_num": trade_num,
            "side": trade.side,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "pnl": trade.pnl,
            "pnl_pct": trade.pnl_pct,
            "hold_bars": None,  # compute from timestamps
            "capital_after": capital,
        },
    )
```

#### 2.1.3 Equity Curve Streaming

Add an optional equity callback that fires every N bars, enabling live
plotting or file streaming without waiting for the full run:

```python
EquityCallback = Callable[[pd.Timestamp, float], None]

# Inside the bar loop:
if equity_callback and (bar_num % equity_interval == 0):
    equity_callback(current_time, capital + unrealized)
```

#### 2.1.4 Signal Generation Tracing

The biggest debugging blind spot: **why did the strategy return HOLD?**
Add a `SignalTrace` dataclass returned alongside the signal.

```python
# src/babs/strategies/base_strategy.py -- new type

from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class SignalTrace:
    """Structured record of why a signal was generated."""
    signal: Signal
    strategy: str
    timestamp: str  # bar timestamp
    indicators: Dict[str, float] = field(default_factory=dict)
    conditions: Dict[str, bool] = field(default_factory=dict)
    rationale: str = ""
```

Each strategy's `generate_signal` returns both:

```python
# src/babs/strategies/macd_strategy.py -- traced signal

def generate_signal_traced(self, data: pd.DataFrame) -> tuple[Signal, SignalTrace]:
    if len(data) < self.required_history():
        return Signal.HOLD, SignalTrace(
            signal=Signal.HOLD,
            strategy="macd",
            timestamp=str(data.index[-1]),
            rationale="insufficient_history",
        )

    df = self._compute_macd(data)
    current_hist = df["macd_hist"].iloc[-1]
    prev_hist = df["macd_hist"].iloc[-2]
    macd_val = df["macd"].iloc[-1]
    signal_val = df["macd_signal"].iloc[-1]

    bullish_cross = prev_hist <= 0 and current_hist > 0
    bearish_cross = prev_hist >= 0 and current_hist < 0

    if bullish_cross:
        sig = Signal.BUY
    elif bearish_cross:
        sig = Signal.SELL
    else:
        sig = Signal.HOLD

    trace = SignalTrace(
        signal=sig,
        strategy="macd",
        timestamp=str(data.index[-1]),
        indicators={
            "macd": float(macd_val),
            "macd_signal": float(signal_val),
            "macd_hist": float(current_hist),
            "macd_hist_prev": float(prev_hist),
            "close": float(data["close"].iloc[-1]),
        },
        conditions={
            "bullish_crossover": bullish_cross,
            "bearish_crossover": bearish_cross,
        },
        rationale=f"hist {prev_hist:.6f} -> {current_hist:.6f}",
    )
    return sig, trace
```

The engine can optionally collect traces:

```python
# In engine.run():
if hasattr(self.strategy, 'generate_signal_traced'):
    signal, trace = self.strategy.generate_signal_traced(history)
    if collect_traces:
        traces.append(trace)
else:
    signal = self.strategy.generate_signal(history)
```

This keeps backward compatibility -- `generate_signal()` stays unchanged,
and `generate_signal_traced()` is opt-in for debugging runs.

### 2.2 Live Trading Monitoring

#### 2.2.1 Order Lifecycle Events

Add a unified event logger to `order_manager.py` that tracks every state
transition with a correlation ID:

```python
import uuid

class OrderManager:
    def place_limit_order(self, token_id, side, price, size):
        correlation_id = str(uuid.uuid4())[:8]

        logger.info("order.attempt", extra={
            "event": "order.attempt",
            "correlation_id": correlation_id,
            "token_id": token_id[:16],
            "side": side,
            "price": price,
            "size": size,
        })

        result = self.client.place_limit_order(token_id, side, price, size)

        if result.success:
            logger.info("order.placed", extra={
                "event": "order.placed",
                "correlation_id": correlation_id,
                "order_id": result.order_id,
            })
        else:
            logger.error("order.rejected", extra={
                "event": "order.rejected",
                "correlation_id": correlation_id,
                "error": result.error,
            })
```

#### 2.2.2 Position State Changes

`position_tracker.py` already logs opens and closes. Enhance with structured
fields and add state-change events:

```python
def open_position(self, ...):
    pos = TrackedPosition(...)
    self._open_positions[key] = pos
    logger.info("position.opened", extra={
        "event": "position.opened",
        "token_id": token_id[:16],
        "side": side,
        "entry_price": entry_price,
        "size": size,
        "account": account,
        "open_count": len(self._open_positions),
    })

def update_price(self, token_id, price, account=""):
    key = self._key(token_id, account)
    if key in self._open_positions:
        pos = self._open_positions[key]
        old_pnl = pos.unrealized_pnl
        pos.current_price = price
        new_pnl = pos.unrealized_pnl
        # Log significant P&L changes (>1% move)
        if abs(new_pnl - old_pnl) / (pos.entry_price * pos.size) > 0.01:
            logger.info("position.pnl_change", extra={
                "event": "position.pnl_change",
                "token_id": token_id[:16],
                "unrealized_pnl": new_pnl,
                "pnl_pct": pos.unrealized_pnl_pct,
            })
```

#### 2.2.3 Risk Manager Decision Logging

The risk manager should return a structured denial reason, not just a bool:

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class RiskDecision:
    allowed: bool
    reason: Optional[str] = None
    details: Optional[dict] = None

class RiskManager:
    def check_trade(self, open_positions) -> RiskDecision:
        self._ensure_today()

        if self.current_drawdown >= self.params.max_drawdown:
            return RiskDecision(
                allowed=False,
                reason="max_drawdown_breached",
                details={
                    "current_drawdown": self.current_drawdown,
                    "limit": self.params.max_drawdown,
                },
            )

        if len(open_positions) >= self.params.max_open_positions:
            return RiskDecision(
                allowed=False,
                reason="max_positions_reached",
                details={
                    "open_count": len(open_positions),
                    "limit": self.params.max_open_positions,
                },
            )

        if self._daily_stats.realized_pnl <= -self.params.max_daily_loss:
            return RiskDecision(
                allowed=False,
                reason="daily_loss_limit",
                details={
                    "daily_pnl": self._daily_stats.realized_pnl,
                    "limit": self.params.max_daily_loss,
                },
            )

        return RiskDecision(allowed=True)

    def can_trade(self, open_positions) -> bool:
        """Backward-compatible wrapper."""
        return self.check_trade(open_positions).allowed
```

The caller (`trader.py`) then logs the decision:

```python
decision = self.risk_manager.check_trade(open_positions)
if not decision.allowed:
    logger.info("risk.blocked", extra={
        "event": "risk.blocked",
        "reason": decision.reason,
        **(decision.details or {}),
    })
    return
```

#### 2.2.4 API Latency Tracking

Wrap every API call with timing:

```python
import time
from contextlib import contextmanager

@contextmanager
def _timed(operation: str):
    t0 = time.monotonic()
    try:
        yield
    finally:
        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info("api.call", extra={
            "event": "api.call",
            "operation": operation,
            "duration_ms": round(elapsed_ms, 1),
        })

# Usage in polymarket_client.py:
def get_order_book(self, token_id):
    with _timed("get_order_book"):
        book = client.get_order_book(token_id)
        # ...
```

#### 2.2.5 Data Freshness

Add a staleness check to the trader's tick method:

```python
def tick(self, data):
    if data is None or data.empty:
        return

    latest_bar_time = data.index[-1]
    now = pd.Timestamp.utcnow()
    staleness = (now - latest_bar_time).total_seconds()

    logger.debug("data.freshness", extra={
        "event": "data.freshness",
        "latest_bar": str(latest_bar_time),
        "staleness_seconds": round(staleness, 1),
    })

    if staleness > parse_timeframe_seconds(self.settings.timeframe) * 3:
        logger.warning("data.stale", extra={
            "event": "data.stale",
            "staleness_seconds": round(staleness, 1),
            "threshold_seconds": parse_timeframe_seconds(self.settings.timeframe) * 3,
        })
```

#### 2.2.6 Heartbeat

Add a periodic heartbeat to the trading loop:

```python
# In trader.py run():
loop_count = 0
while self._running:
    loop_count += 1
    try:
        data = self._fetch_latest_data()
        if data is not None and not data.empty:
            self.tick(data)

        if loop_count % 10 == 0:  # every ~5 min at 30s poll
            logger.info("heartbeat", extra={
                "event": "heartbeat",
                "loop_count": loop_count,
                "equity": self.risk_manager.current_equity,
                "open_positions": len(self.position_tracker.get_open_positions()),
                "daily_pnl": self.risk_manager._daily_stats.realized_pnl,
            })
    except Exception:
        logger.exception("Error in trading loop")
    time.sleep(self.settings.poll_interval_seconds)
```

### 2.3 Strategy Debugging

#### Per-Bar Indicator Dump

For debugging runs, add a `--trace-bars` flag to the backtest CLI that writes
a CSV of every bar's indicator values:

```
# Produced by the engine when trace mode is on:
# timestamp, close, macd, macd_signal, macd_hist, signal, position_side, equity
```

This uses the `SignalTrace` mechanism from 2.1.4. The engine collects all
traces and writes them to a file after the run:

```python
def _write_trace_csv(traces: list[SignalTrace], path: str):
    import csv
    if not traces:
        return
    fieldnames = ["timestamp", "signal", "strategy", "rationale"]
    # Collect all indicator keys across traces
    all_indicators = set()
    for t in traces:
        all_indicators.update(t.indicators.keys())
    fieldnames.extend(sorted(all_indicators))

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in traces:
            row = {
                "timestamp": t.timestamp,
                "signal": t.signal.value,
                "strategy": t.strategy,
                "rationale": t.rationale,
            }
            row.update(t.indicators)
            writer.writerow(row)
```

---

## 3. Technology Recommendations

### 3.1 Logging: structlog over stdlib

**Recommendation: `structlog`** with stdlib as the backend.

Rationale:
- This is a single-developer project. structlog adds structured
  key-value logging with zero config overhead.
- It works *on top of* stdlib logging -- not a replacement. All
  existing `logging.getLogger(__name__)` calls keep working.
- You get JSON output for production and colorized console output for
  development with one config change.
- The `extra={}` patterns shown above become cleaner:

```python
import structlog
logger = structlog.get_logger()

# Instead of:
logger.info("order.placed", extra={"order_id": oid, "price": price})

# You write:
logger.info("order.placed", order_id=oid, price=price)
```

**Setup (one-time, in cli.py):**

```python
import structlog

def _setup_logging(log_level: str, json_output: bool = False) -> None:
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
    )
```

### 3.2 Metrics: Simple File-Based, Not Prometheus

**Recommendation: Skip Prometheus/OpenTelemetry for now.** Use a simple
metrics collector that writes to a JSON file.

Rationale:
- Prometheus requires running a metrics server. Overkill for a single bot.
- OpenTelemetry is a complex dependency chain for minimal benefit here.
- A simple in-process counter/gauge class that periodically dumps to
  `data/metrics.json` gives 80% of the value at 5% of the complexity.

```python
# src/babs/observability/metrics.py

import json
import time
from collections import defaultdict
from pathlib import Path
from threading import Lock

class Metrics:
    """Dead-simple in-process metrics collector."""

    def __init__(self):
        self._counters: dict[str, int] = defaultdict(int)
        self._gauges: dict[str, float] = {}
        self._lock = Lock()

    def inc(self, name: str, value: int = 1):
        with self._lock:
            self._counters[name] += value

    def gauge(self, name: str, value: float):
        with self._lock:
            self._gauges[name] = value

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "timestamp": time.time(),
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
            }

    def dump(self, path: str = "data/metrics.json"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.snapshot(), f, indent=2)

# Global singleton
metrics = Metrics()
```

Usage:

```python
from babs.observability.metrics import metrics

# In order_manager.py:
metrics.inc("orders.placed")
metrics.inc("orders.rejected")

# In trader.py:
metrics.gauge("equity", self.risk_manager.current_equity)
metrics.gauge("open_positions", len(self.position_tracker.get_open_positions()))

# In polymarket_client.py:
metrics.inc("api.calls.get_order_book")
```

### 3.3 Tracing: Correlation IDs, Not OpenTelemetry

**Recommendation: Use `structlog.contextvars` for trace context.**

```python
import structlog
from contextvars import ContextVar

trade_id_var: ContextVar[str] = ContextVar("trade_id", default="")

# At the start of each tick:
import uuid
structlog.contextvars.bind_contextvars(
    tick_id=str(uuid.uuid4())[:8],
    token_id=self.token_id[:16],
)

# All subsequent log calls in that tick automatically include tick_id
# and token_id without any extra= boilerplate.
```

### 3.4 Technology Summary

| Concern | Recommendation | Dependency | Reason |
|---------|---------------|------------|--------|
| Structured logging | `structlog` | 1 package | Clean API, stdlib compatible |
| Metrics | Custom `Metrics` class | 0 packages | Minimal, no server needed |
| Tracing | `contextvars` + correlation IDs | 0 packages | Built into Python |
| Progress bars | `rich` (already common) | 1 package | Great CLI UX |
| Alerting | Log-based (grep for WARNING/ERROR) | 0 packages | Good enough for solo dev |

Total new dependencies: **1-2 packages** (structlog, optionally rich).

---

## 4. Implementation Approach

### 4.1 Files That Need to Change

| File | Change Type | Scope |
|------|------------|-------|
| `cli.py` | Logging setup, progress flags | Small |
| `backtesting/engine.py` | Progress callback, trade events, trace collection | Medium |
| `strategies/base_strategy.py` | Add `SignalTrace` dataclass, `generate_signal_traced()` | Small |
| `strategies/macd_strategy.py` | Add `generate_signal_traced()` | Small |
| `strategies/rsi_mean_reversion.py` | Add `generate_signal_traced()` | Small |
| `strategies/cvd_strategy.py` | Add `generate_signal_traced()` | Small |
| `bot/trader.py` | Heartbeat, data freshness, structured events | Medium |
| `bot/order_manager.py` | Correlation IDs, structured events | Small |
| `bot/risk_manager.py` | Return `RiskDecision` instead of `bool` | Small-Medium |
| `bot/position_tracker.py` | Structured events on state changes | Small |
| `data/polymarket_client.py` | API timing wrapper | Small |
| **New:** `observability/__init__.py` | Package init | Trivial |
| **New:** `observability/metrics.py` | Simple metrics collector | Small |

### 4.2 Preserving Public Interfaces

Every change can be made **without breaking existing callers**:

1. **`generate_signal()` stays unchanged.** The new `generate_signal_traced()`
   is an *additional* method. The engine checks for its existence with
   `hasattr()`. Strategies that don't implement it work exactly as before.

2. **`can_trade()` return type change** is the one breaking change. To avoid
   it, add a new method `check_trade()` that returns `RiskDecision`, and keep
   `can_trade()` as a thin wrapper:

   ```python
   def check_trade(self, open_positions) -> RiskDecision:
       # ... full implementation ...

   def can_trade(self, open_positions) -> bool:
       """Backward-compatible wrapper."""
       return self.check_trade(open_positions).allowed
   ```

3. **`BacktestEngine.run()`** gains optional kwargs (`progress_callback`,
   `progress_interval`, `collect_traces`). All default to None/False, so
   existing callers are unaffected.

4. **Logging changes** (stdlib -> structlog) are invisible to callers.
   `structlog.get_logger()` returns a logger that behaves identically from
   the caller's perspective.

### 4.3 Making It Opt-In

The instrumentation should be **zero-cost by default**:

**CLI flags to enable instrumentation:**

```
babs backtest --strategy macd ... --progress --trace-bars
babs bot --strategy macd ... --json-logs --metrics-file data/metrics.json
```

**Configuration-driven:**

```python
@dataclass
class ObservabilityConfig:
    structured_logging: bool = False   # JSON logs vs plain text
    collect_traces: bool = False       # Signal traces (backtest only)
    progress_reporting: bool = True    # Progress callback
    progress_interval: int = 2000      # Bars between progress updates
    api_timing: bool = False           # Measure API call durations
    metrics_file: str = ""             # Empty = disabled
    heartbeat_interval: int = 10       # Ticks between heartbeats (0 = off)
```

**Conditional instrumentation in hot paths:**

```python
# In engine.py -- the bar loop is the hottest path
# Only check for traces if explicitly requested
if self._collect_traces and hasattr(self.strategy, 'generate_signal_traced'):
    signal, trace = self.strategy.generate_signal_traced(history)
    self._traces.append(trace)
else:
    signal = self.strategy.generate_signal(history)
```

The `if` check is a single boolean test -- negligible cost. The
`generate_signal_traced()` method computes the same indicators as
`generate_signal()` (it calls the same `_compute_macd()` etc.), so the
extra cost is only the dataclass allocation, which is ~microseconds per bar.

**Performance guardrails:**

- Progress callbacks fire every N bars (default 2000), not every bar.
- API timing uses `time.monotonic()` (nanosecond precision, no syscall overhead).
- Metrics collector uses a simple dict with a lock -- no allocation per update.
- Signal traces are only collected when `--trace-bars` is passed.
- structlog's bound loggers are lazily evaluated -- if the log level filters
  out DEBUG, the formatting cost is zero.

### 4.4 Implementation Order

Recommended sequence, each independently shippable:

1. **Progress reporting in `engine.py`** -- highest user-visible impact,
   smallest change. Solves the "30 seconds of silence" problem immediately.

2. **structlog setup in `cli.py`** -- foundational change that makes all
   subsequent instrumentation cleaner.

3. **`SignalTrace` and `generate_signal_traced()`** -- strategy debugging,
   the second most requested capability.

4. **API timing and data freshness** -- important for live trading reliability.

5. **`RiskDecision` and structured order events** -- completes the live
   trading observability story.

6. **Simple metrics collector** -- nice-to-have for long-running bots.

Each step is a single PR with no dependency on the others (except step 2
makes steps 3-6 cleaner).
