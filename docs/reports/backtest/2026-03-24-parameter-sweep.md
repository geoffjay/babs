# Parameter Sweep Report — 2026-03-24

## Overview

1,440 strategy configurations tested across 2 symbols (BTC/USDT, ETH/USDT),
2 timeframes (1h, 4h), and 360 parameter combinations per dataset.

- **MACD**: fast [8,12] × slow [21,26,34] × signal [5,9] × SL [3%,5%,7%] × TP [5%,10%,15%]
- **RSI**: period [7,14,21] × oversold [20,30] × overbought [70,80] × SL × TP
- **CVD**: lookback [10,15,20,30] × divergence [0.005,0.01,0.02,0.03] × SL × TP

Initial capital: $1,000 | Position size: 0.01 units | Slippage: 0.1%
Period: Jan 1 – Mar 1, 2025

Full results: `sweep_results.csv` (1,440 rows)

## Summary by Strategy

| Strategy | Active Configs | Profitable | Rate  | Avg Return | Best Sharpe |
|----------|---------------|------------|-------|------------|-------------|
| CVD      | 576           | 393        | 68.2% | -0.17%     | 5.13        |
| RSI      | 423           | 124        | 29.3% | -2.83%     | 3.87        |
| MACD     | 432           | 68         | 15.7% | -11.26%    | 1.11        |

**414 configurations achieved Sharpe > 1.0**, almost all CVD on ETH/USDT.

## Top 10 Configurations

| # | Strategy | Symbol   | TF | Sharpe | Return | Win Rate | PF   | Trades | Key Params |
|---|----------|----------|----|--------|--------|----------|------|--------|------------|
| 1 | CVD      | ETH/USDT | 4h | 5.13   | +0.97% | 77.3%    | 8.29 | 22     | lookback=20, div=0.01 |
| 2 | CVD      | ETH/USDT | 4h | 4.78   | +0.91% | 69.6%    | 6.79 | 23     | lookback=20, div=0.005 |
| 3 | CVD      | ETH/USDT | 1h | 4.38   | +0.60% | 75.0%    | 4.63 | 8      | lookback=30, div=0.03 |
| 4 | CVD      | ETH/USDT | 4h | 4.38   | +0.74% | 72.7%    | 3.64 | 22     | lookback=20, div=0.01, SL=3% |
| 5 | CVD      | ETH/USDT | 1h | 4.36   | +0.59% | 77.8%    | 4.59 | 9      | lookback=30, div=0.03 |
| 6 | RSI      | ETH/USDT | 4h | 3.87   | +0.57% | 83.3%    | 3.40 | 6      | period=21, OS=30, OB=70 |
| 7 | CVD      | ETH/USDT | 4h | 3.82   | +0.68% | 84.6%    | varies | 13   | lookback=20, div=0.02 |
| 8 | CVD      | ETH/USDT | 4h | 3.73   | +0.63% | 88.9%    | varies | 9    | lookback=20, div=0.03 |
| 9 | RSI      | BTC/USDT | 4h | 3.59   | +3.92% | 100.0%   | inf  | 1      | period=21, OS=20, OB=80 |
| 10| CVD      | ETH/USDT | 1h | 3.63   | +0.26% | 66.7%    | varies | 6    | lookback=10, div=0.03 |

## Best Config per Strategy/Timeframe

| Strategy | TF | Best Sharpe | Return | Win Rate | PF   | Trades |
|----------|-----|------------|--------|----------|------|--------|
| CVD      | 4h  | 5.13       | +0.97% | 77.3%    | 8.29 | 22     |
| CVD      | 1h  | 4.38       | +0.60% | 75.0%    | 4.63 | 8      |
| RSI      | 4h  | 3.87       | +0.57% | 83.3%    | 3.40 | 6      |
| RSI      | 1h  | 3.53       | +0.41% | 75.0%    | 2.68 | 8      |
| MACD     | 1h  | 1.11       | +0.41% | 38.2%    | 1.12 | 123    |
| MACD     | 4h  | -0.30      | -0.10% | 29.6%    | 0.94 | 27     |

## Key Findings

### 1. CVD Dominates — ETH/USDT is the Sweet Spot

Every top config is CVD on ETH/USDT. The best (Sharpe 5.13, PF 8.29) uses
`lookback=20, divergence_threshold=0.01` on 4h candles. This config:
- Wins 77% of trades
- Makes 8.3x more on winners than losers
- Trades ~22 times in 2 months (moderate frequency)

The lookback=20 parameter dominates — it appears in 18 of the top 25 configs.
This suggests 20 bars (80 hours on 4h, 20 hours on 1h) is the natural divergence
cycle for ETH.

### 2. SL/TP Parameters Don't Matter for CVD

The same CVD config with different SL/TP values produces nearly identical results.
This means the divergence-resolution exit dominates — trades almost never hit
stop-loss or take-profit. The exit logic (price and CVD moving in the same direction)
triggers before SL/TP thresholds.

**Implication**: The CVD strategy's edge is entirely in its entry timing and its
divergence-resolution exit. SL/TP are safety nets that rarely fire.

### 3. MACD Should Be Abandoned or Completely Reworked

- Only 15.7% of configs profitable (vs 68.2% for CVD)
- Best Sharpe is 1.11 — barely positive, with 123 trades
- Average return across all configs: -11.26%
- Even with slower params (8/26/9, 12/34/9), the strategy loses money
- The MACD histogram crossover approach is not viable for crypto on any tested timeframe

### 4. RSI Has Niche Potential on Longer Timeframes

- RSI with `period=21, oversold=30, overbought=70` on ETH/USDT 4h: Sharpe 3.87
- But only 6 trades — statistically insignificant
- The 100% win rate RSI configs (1 trade) are noise, not signal
- RSI needs more data (longer backtest period) to validate

### 5. Returns Are Small Because Position Size Is Conservative

Position size of 0.01 units means ~$33 per ETH trade. The +0.97% return on $1,000
is about $9.70 over 2 months. With larger position sizing (e.g., 10% of capital per
trade), the CVD configs would produce ~10x returns — but also 10x drawdowns.

## Caveats

1. **2-month window is short** — the extended market tests (6-month) showed CVD
   losing 34-38% on the same assets. This sweep's results may be regime-dependent.

2. **No out-of-sample validation** — all configs were tested on the same data used
   to select them. Walk-forward analysis is needed.

3. **Low trade count** — 22 trades is not statistically robust. With 22 trades and
   77% win rate, a 95% confidence interval for the true win rate is ~55-92%.

4. **Slippage model is simplistic** — fixed 0.1% doesn't reflect real-world
   spread or market impact.

## Recommendations

### For CVD Development
- Run walk-forward: optimize on Jan 2024–Jun 2024, validate on Jul 2024–Dec 2024
- Test on 6+ months of data with the best params (lookback=20, div=0.01)
- Focus on ETH — it consistently outperforms BTC across all tests
- Consider: is the edge from actual volume dynamics, or from OHLC bar shape?

### For the Engine
- Add fractional position sizing (% of capital per trade)
- Add buy-and-hold benchmark comparison
- Add trade-level logging for post-analysis
- Make the sweep script a first-class CLI command (`babs sweep`)

### For MACD
- Either remove the strategy entirely, or replace with a fundamentally different
  momentum approach (e.g., dual momentum, trend-following with longer lookback)

### For RSI
- Test on longer periods (12+ months) to get statistically significant trade counts
- Consider combining with CVD as a filter (enter on CVD divergence only when RSI
  confirms oversold/overbought)
