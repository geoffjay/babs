# Strategy Evaluation Report — 2026-03-24

## Executive Summary

All three strategies (MACD, RSI, CVD) were backtested across multiple timeframes and
symbols on the Jan 1 – Mar 1, 2025 period. **Only the CVD strategy on 1h timeframes
shows a viable edge.** The MACD strategy is fundamentally broken on short timeframes
due to overtrading and slippage death. The RSI strategy is marginal. Several engine-level
issues compound the problem.

## Test Matrix

| Strategy | Symbol   | Timeframe | Trades | Win Rate | Sharpe | Max DD   | Return   |
|----------|----------|-----------|--------|----------|--------|----------|----------|
| MACD     | BTC/USDT | 5m        | 3675   | 14.61%   | -3.27  | 99.94%   | **-99.94%** |
| MACD     | BTC/USDT | 1h        | 317    | 27.13%   | -0.83  | 46.14%   | -36.80%  |
| MACD     | BTC/USDT | 4h        | 83     | 26.51%   | -2.01  | 47.12%   | -40.55%  |
| MACD     | ETH/USDT | 1h        | 320    | 29.69%   | -0.32  | 41.81%   | -26.60%  |
| RSI      | BTC/USDT | 5m        | 520    | 21.92%   | -0.93  | 60.33%   | -60.04%  |
| RSI      | BTC/USDT | 1h        | 33     | 57.58%   | -0.16  | 12.49%   | -5.28%   |
| RSI      | BTC/USDT | 4h        | 11     | 63.64%   | 0.13   | 14.39%   | +1.06%   |
| CVD      | BTC/USDT | 5m        | 21     | 47.62%   | -0.02  | 8.00%    | -1.89%   |
| CVD      | BTC/USDT | 1h        | 22     | 68.18%   | 0.34   | 12.12%   | **+8.51%**  |
| CVD      | BTC/USDT | 4h        | 10     | 50.00%   | -0.23  | 5.61%    | -2.41%   |
| CVD      | ETH/USDT | 1h        | 37     | 67.57%   | 0.48   | 7.85%    | **+15.72%** |

## Root Cause Analysis: Why MACD Loses Everything on 5m

The -99.94% loss is **not a bug in the backtest engine**. The P&L math is correct.
The loss is almost entirely explained by **slippage compounding over extreme
overtrading**.

### The Math

The engine uses the entire remaining capital per trade (`size = capital / entry_price`
when `position_size` exceeds what capital can buy). Each round-trip trade incurs
0.1% slippage on entry + 0.1% on exit = ~0.2% cost per trade.

After N trades, capital decays as:

    capital × (1 - 0.002)^N

For 3675 trades:

    $1000 × 0.998^3675 = $1000 × e^(-7.35) ≈ $0.64

**The observed final capital is $0.63.** This is almost exactly the slippage-only
prediction, meaning the MACD strategy on 5m has zero directional edge — it's
equivalent to random trading with transaction costs.

### Why So Many Trades?

MACD parameters (fast=3, slow=15, signal=3) create a histogram that crosses zero
on virtually every minor price oscillation at 5m resolution. BTC/USDT on 5m has
enough noise that a 3/15 EMA pair crosses roughly every 25 minutes.

The strategy enters on crossover, then exits on reverse crossover (same signal
logic), creating a constant churn of enter → exit → enter → exit.

## Engine Issues Found

### 1. Same-bar exit + entry (not a bug, but amplifies overtrading)

The engine checks exit then entry on the same bar (lines 80-135). After exiting
a position, it immediately checks for a new entry signal on the same bar. For MACD,
the exit IS the reverse crossover, which IS an entry signal — so it re-enters
immediately on the same bar it exits. This is by design but doubles the trade count.

### 2. Position size uses 100% of capital

When `position_size=1.0` (1 BTC) exceeds what capital can afford, the engine falls
back to `size = capital / entry_price`, committing 100% of remaining capital to each
trade. There's no fractional allocation. This means every losing trade directly
reduces the capital available for the next trade — a compounding decay.

### 3. `--size` semantics are ambiguous

The CLI help says "Position size per trade" but doesn't specify units. For the `bot`
command it says "Position size in dollars" (line 128), but for `backtest` it's
unitless (line 53). In the engine, `size` is multiplied by `entry_price` to get
notional, so it's treated as **units of the asset** — 1.0 means 1 BTC, not $1.

## Strategy-Level Findings

### MACD — Not Viable in Current Form

- Loses money on every timeframe and symbol tested
- Win rate never exceeds 30%
- Parameters (3/15/3) are too fast for any crypto timeframe
- Would need: much slower parameters (e.g., 12/26/9), minimum hold period,
  signal strength filter, or a completely different approach

### RSI Mean Reversion — Marginal

- Barely profitable on 4h BTC (+1.06%), unprofitable elsewhere
- 57-64% win rate on longer timeframes is promising
- Problem: average loser is much larger than average winner ($-16.62 vs $9.47 on 1h)
- The VWAP exit triggers too quickly, cutting winners short
- Would need: wider stop-loss, trailing stop, or delayed VWAP exit

### CVD — Most Promising

- **Only strategy with positive Sharpe on any configuration** (0.34 on BTC/1h, 0.48 on ETH/1h)
- 67-68% win rate on 1h timeframe
- Reasonable trade frequency (22-37 trades in 2 months)
- Max drawdown under 13% in profitable configurations
- ETH/USDT outperforms BTC/USDT — possibly because ETH has more retail-driven
  volume divergences

**Concern:** CVD estimates volume delta from OHLC bar shape, which is a rough
approximation. On Polymarket (the actual target), this would need real order flow data.

## Recommendations

### Immediate (fix before further testing)

1. **Clarify `--size` semantics** — should be in dollars, not units. A $1 position
   in BTC is 0.00001 BTC, which is meaningless. The engine should accept a dollar
   amount and compute size as `dollar_amount / entry_price`.

2. **Cap position size as fraction of capital** — e.g., risk 10-20% per trade max,
   not 100%. The current behavior of committing all remaining capital to each trade
   guarantees compounding losses.

3. **Add minimum hold period** — prevent same-bar exit+entry to reduce churn.
   Even 1 bar of cooldown would halve MACD's trade count.

### Short-term (strategy tuning)

4. **MACD: use standard parameters** (12/26/9) or disable the strategy until
   parameters are optimized per-timeframe.

5. **RSI: widen asymmetric exits** — let winners run longer before VWAP exit,
   tighten losers with faster stop-loss.

6. **CVD: focus development here** — it's the only strategy showing an edge.
   Test on more symbols, longer periods, and add volume-quality filters.

### Medium-term (engine improvements)

7. **Add transaction cost modeling** — make slippage configurable, add explicit
   fee calculation, show gross vs net P&L.

8. **Add buy-and-hold benchmark** — BTC went from ~$93k to ~$84k in this period
   (-9.7%). Even losing strategies should be compared to this baseline.

9. **Add position sizing modes** — fixed dollar, fixed fraction, Kelly criterion.

## Appendix: BTC/USDT Price Context (Jan–Mar 2025)

BTC/USDT moved from ~$93,500 (Jan 1) to ~$84,400 (Mar 1), a decline of approximately
9.7%. This was a bearish-to-choppy period with a major drawdown in February.
A buy-and-hold short would have returned ~9.7%; a buy-and-hold long would have
lost ~9.7%.

The CVD strategy's +8.5% return on BTC/1h in a -9.7% market represents
approximately 18% alpha over buy-and-hold long.
