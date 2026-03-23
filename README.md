# BABS - Polymarket Algorithmic Trading Bot

An algorithmic trading bot for [Polymarket](https://polymarket.com/) prediction markets, built on the **RBI methodology** (Research → Backtest → Incubate). Uses limit orders only via the [py-clob-client](https://github.com/Polymarket/py-clob-client) SDK.

## Why Algorithmic Trading?

Manual trading is fighting your own biology. The amygdala reacts in 12ms; the prefrontal cortex takes 500ms — a 40x gap. By the time logic kicks in, emotion has already hit "sell." The result: panic sells at bottoms, FOMO buys at tops, revenge trades, and frozen positions.

This bot removes the amygdala from the equation. It executes the strategy — nothing more, nothing less.

## The RBI System

Every strategy goes through three stages before it earns real capital:

### 1. Research
Find proven strategies from existing sources rather than inventing from scratch:
- **Market Wizards** (Jack Schwager) — interviews with verified profitable traders
- **Chat with Traders** podcast — 300+ episodes of real trader insights
- **Google Scholar** — search "mean reversion trading strategies" or "momentum crypto strategies" for PhD-level research
- **Small-size live trading** ($1-10) — observe patterns, not for profit

### 2. Backtest
Run every strategy against historical data before risking a dollar. A backtest reveals the truth in minutes — not weeks of live losses. See [Running a Backtest](#running-a-backtest) below.

### 3. Incubate
Start with $1. Observe for 2-4 weeks. Scale slowly: **$1 → $5 → $10 → $50 → $100**. Never skip straight from backtest to large size — 90% of people get this wrong.

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure your wallet

Copy the example environment file and fill in your Polymarket wallet credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```
POLYMARKET_PRIVATE_KEY=0xYourPrivateKeyHere
POLYMARKET_FUNDER_ADDRESS=0xYourWalletAddressHere
```

Your private key is the Polygon wallet key that has been approved on Polymarket. The funder address is the corresponding wallet address. **Never commit your `.env` file** — it's already in `.gitignore`.

### 3. Find a market to trade

Browse [Polymarket](https://polymarket.com/) and find an active market. You'll need the **condition token ID** for the outcome you want to trade. This can be found in the market's URL or via the API.

### 4. Run a backtest

```bash
python deploy/run_backtest.py \
  --strategy macd \
  --symbol BTC/USDT \
  --timeframe 5m \
  --start-date 2025-01-01 \
  --end-date 2025-03-01 \
  --size 1
```

**Benchmarks for a profitable strategy:**

| Metric | Minimum Target |
|---|---|
| Win rate | > 55% |
| Profit factor | > 1.5 |
| Max drawdown | < 20% |
| Sample size | At least 100 trades |

If the strategy doesn't pass — move on. Don't get attached to ideas.

**All available backtest flags:**

| Flag | Default | Description |
|---|---|---|
| `--strategy` | *(required)* | `macd`, `rsi`, or `cvd` |
| `--symbol` | `BTC/USDT` | Trading pair for data download |
| `--timeframe` | `1h` | Candle timeframe (`1m`, `5m`, `1h`, etc.) |
| `--start-date` | *(required)* | Start date `YYYY-MM-DD` |
| `--end-date` | *(required)* | End date `YYYY-MM-DD` |
| `--capital` | `1000` | Initial simulated capital |
| `--size` | `1` | Position size per trade |
| `--exchange` | `binance` | Exchange for OHLCV data (via ccxt) |
| `--use-cache` | off | Reuse previously downloaded data |

### 5. Launch the bot (incubation mode)

Start with **$1 size** — this is incubation, not production:

```bash
python deploy/run_bot.py \
  --strategy macd \
  --token-id YOUR_TOKEN_ID \
  --size 1 \
  --account primary
```

**All available bot flags:**

| Flag | Default | Description |
|---|---|---|
| `--strategy` | *(required)* | `macd`, `rsi`, or `cvd` |
| `--token-id` | *(required)* | Polymarket condition token ID |
| `--size` | `1` | Position size in dollars |
| `--account` | `primary` | Account name (see [Multi-Account Setup](#multi-account-setup)) |
| `--log-level` | `INFO` | `DEBUG`, `INFO`, `WARNING`, or `ERROR` |

Check every few hours: any errors? Are orders filling? Does P&L match backtest expectations?

### 6. Monitor

```bash
python deploy/run_monitor.py --interval 30
```

---

## Strategies

### MACD Histogram (fast=3, slow=15, signal=3)

Best for: **trending moves within 5-minute windows.**

- **Entry:** MACD line crosses signal line (histogram sign change)
- **Exit:** Reverse crossover, stop-loss (5%), or take-profit (10%)
- Historical benchmark on Polymarket 5m markets: ~60% win rate

```bash
python deploy/run_bot.py --strategy macd --token-id TOKEN --size 1
```

### RSI Mean Reversion (RSI 14)

Best for: **pullbacks after sharp moves.**

- **Entry:** RSI < 30 (oversold) → long; RSI > 70 (overbought) → short
- **Exit:** RSI reverts to 50, price reaches VWAP, or stop-loss/take-profit
- Historical benchmark: ~59% win rate

```bash
python deploy/run_bot.py --strategy rsi --token-id TOKEN --size 1
```

### CVD (Cumulative Volume Delta)

Best for: **identifying reversal points.**

- **Entry:** Price drops + CVD rises = hidden buying pressure → long. Price rises + CVD falls → short.
- **Exit:** Divergence resolves, or stop-loss/take-profit
- Historical benchmark: ~63% win rate

```bash
python deploy/run_bot.py --strategy cvd --token-id TOKEN --size 1
```

---

## Multi-Account Setup

Each bot should run on its own Polymarket account to isolate strategies and risk. Add numbered accounts to `.env`:

```
# Primary account
POLYMARKET_PRIVATE_KEY=0x...
POLYMARKET_FUNDER_ADDRESS=0x...

# Account 2
POLYMARKET_PRIVATE_KEY_2=0x...
POLYMARKET_FUNDER_ADDRESS_2=0x...

# Account 3
POLYMARKET_PRIVATE_KEY_3=0x...
POLYMARKET_FUNDER_ADDRESS_3=0x...
```

Then reference them by name:

```bash
# Terminal 1 — MACD bot
python deploy/run_bot.py --strategy macd --token-id TOKEN --account primary

# Terminal 2 — RSI bot
python deploy/run_bot.py --strategy rsi --token-id TOKEN --account account_2

# Terminal 3 — CVD bot
python deploy/run_bot.py --strategy cvd --token-id TOKEN --account account_3

# Terminal 4 — monitoring
python deploy/run_monitor.py
```

---

## Risk Management

The bot enforces hard risk limits that **cannot be overridden by strategy signals**:

| Parameter | Default | Description |
|---|---|---|
| Stop-loss | 5% | Per-trade maximum loss |
| Take-profit | 10% | Per-trade profit target |
| Max drawdown | 20% | Halt all trading if peak-to-trough exceeds this |
| Max open positions | 3 | Concurrent position limit |
| Max daily loss | $50 | Stop trading for the day after this loss |
| Max position size | $100 | Per-position notional cap |

These defaults are in `config/settings.py` and can be adjusted.

### Incubation Scaling

The position scaler in `incubation/scaler.py` adjusts size automatically based on recent performance:
- **Scale up (1.25x):** Win rate > 60% AND profit factor > 1.5 over last 20 trades
- **Scale down (0.75x):** Win rate < 40% OR profit factor < 0.8
- **Bounds:** $0.50 minimum, $10 maximum (during incubation)

---

## Project Structure

```
├── config/
│   ├── settings.py            # All tunable parameters
│   └── accounts.py            # Multi-account wallet loader
├── data/
│   ├── polymarket_client.py   # Polymarket CLOB API (limit orders only)
│   ├── downloader.py          # OHLCV data via ccxt
│   └── storage.py             # CSV/SQLite persistence
├── strategies/
│   ├── base_strategy.py       # Abstract base class + Signal enum
│   ├── macd_strategy.py       # MACD Histogram (3/15/3)
│   ├── rsi_mean_reversion.py  # RSI Mean Reversion + VWAP
│   └── cvd_strategy.py        # Cumulative Volume Delta
├── backtesting/
│   ├── engine.py              # Backtest simulation engine
│   ├── metrics.py             # Win rate, Sharpe, profit factor, drawdown
│   └── runner.py              # Parallel backtest execution
├── bot/
│   ├── trader.py              # Main trading loop
│   ├── risk_manager.py        # Hard risk limits
│   ├── order_manager.py       # Cancel-before-place, dedup
│   └── position_tracker.py    # Position and P&L tracking
├── incubation/
│   ├── monitor.py             # Live bot monitoring dashboard
│   ├── scaler.py              # Adaptive position sizing
│   └── logger.py              # CSV trade log
├── deploy/
│   ├── run_bot.py             # Launch a trading bot
│   ├── run_backtest.py        # Run a backtest
│   └── run_monitor.py         # Launch monitoring dashboard
└── tests/
    ├── test_strategies.py
    ├── test_backtesting.py
    └── test_risk_manager.py
```

---

## Adding a New Strategy

1. Create a new file in `strategies/` that subclasses `BaseStrategy`:

```python
from strategies.base_strategy import BaseStrategy, Position, Signal

class MyStrategy(BaseStrategy):
    name = "mystrategy"

    def generate_signal(self, data):
        # Return Signal.BUY, Signal.SELL, or Signal.HOLD
        ...

    def should_exit(self, position, data):
        # Return True to close the position
        ...
```

2. Register it in `deploy/run_bot.py` and `deploy/run_backtest.py`:

```python
STRATEGY_MAP["mystrategy"] = MyStrategy
```

3. Backtest it. If it passes the benchmarks (>55% win rate, >1.5 profit factor, <20% drawdown, 100+ trades), incubate it.

---

## Important Notes

- **Limit orders only.** The bot never places market orders. This avoids slippage on Polymarket's orderbook.
- **Cancel before place.** All existing orders are cancelled before placing new ones — this prevents duplicate or stale orders.
- **Polygon network.** Polymarket runs on Polygon (chain ID 137). Your wallet needs MATIC for gas and USDC for trading.
- **API credentials** are derived automatically on first connection via `create_or_derive_api_creds()`.
- **A backtest is not a guarantee.** What worked in the past may not work in the future. But it's 100x better than guessing.
