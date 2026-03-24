# Extended Backtest Results: Multiple Markets, Timeframes & Strategies

**Date:** 2026-03-24
**Position Size:** 1 unit per trade
**Initial Capital:** $1,000

---

## Results Summary

### Group 1: More Symbols on 1h (Jan 2025 - Mar 2025)

| # | Strategy | Symbol    | TF | Trades | Win Rate | PF   | Sharpe | Max DD     | Total PnL   | Return  |
|---|----------|-----------|----|--------|----------|------|--------|------------|-------------|---------|
| 1 | CVD      | SOL/USDT  | 1h | 42     | 59.52%   | 0.74 | -0.25  | 8.88%      | -$38.73     | -3.87%  |
| 2 | CVD      | DOGE/USDT | 1h | 36     | 66.67%   | 1.16 | 0.12   | 0.01%      | +$0.02      | +0.00%  |
| 3 | RSI      | ETH/USDT  | 1h | 39     | 51.28%   | 0.69 | -0.30  | 23.65%     | -$160.19    | -16.02% |
| 4 | RSI      | SOL/USDT  | 1h | 38     | 42.11%   | 0.42 | -0.77  | 15.17%     | -$132.86    | -13.29% |

### Group 2: Longer Date Range - 6 Months (Jul 2024 - Jan 2025)

| # | Strategy | Symbol    | TF | Trades | Win Rate | PF   | Sharpe | Max DD     | Total PnL   | Return  |
|---|----------|-----------|----|--------|----------|------|--------|------------|-------------|---------|
| 5 | CVD      | BTC/USDT  | 1h | 89     | 58.43%   | 0.52 | -0.51  | 39.56%     | -$376.06    | -37.61% |
| 6 | CVD      | ETH/USDT  | 1h | 112    | 62.50%   | 0.63 | -0.34  | 37.44%     | -$344.53    | -34.45% |
| 7 | MACD     | BTC/USDT  | 1h | 998    | 26.15%   | 0.56 | -1.53  | 93.25%     | -$929.20    | -92.92% |
| 8 | RSI      | BTC/USDT  | 1h | 142    | 47.18%   | 0.52 | -0.51  | 42.74%     | -$405.11    | -40.51% |

### Group 3: 15m Timeframe (Jan 2025 - Mar 2025)

| # | Strategy | Symbol    | TF  | Trades | Win Rate | PF   | Sharpe | Max DD     | Total PnL   | Return  |
|---|----------|-----------|-----|--------|----------|------|--------|------------|-------------|---------|
| 9 | CVD      | BTC/USDT  | 15m | 28     | 35.71%   | 0.14 | -0.62  | 29.88%     | -$281.04    | -28.10% |
|10 | CVD      | ETH/USDT  | 15m | 68     | 61.76%   | 0.56 | -0.31  | 29.17%     | -$250.35    | -25.03% |
|11 | RSI      | BTC/USDT  | 15m | 185    | 39.46%   | 0.51 | -0.45  | 25.73%     | -$243.08    | -24.31% |
|12 | MACD     | BTC/USDT  | 15m | 1339   | 19.64%   | 0.31 | -2.53  | 94.76%     | -$947.40    | -94.74% |

---

## Consolidated View: All 12 Runs Ranked by Return

| Rank | Strategy | Symbol    | TF  | Period              | Return  | PF   | Sharpe | Max DD  |
|------|----------|-----------|-----|---------------------|---------|------|--------|---------|
| 1    | CVD      | DOGE/USDT | 1h  | Jan-Mar 2025        | +0.00%  | 1.16 | 0.12   | 0.01%   |
| 2    | CVD      | SOL/USDT  | 1h  | Jan-Mar 2025        | -3.87%  | 0.74 | -0.25  | 8.88%   |
| 3    | RSI      | SOL/USDT  | 1h  | Jan-Mar 2025        | -13.29% | 0.42 | -0.77  | 15.17%  |
| 4    | RSI      | ETH/USDT  | 1h  | Jan-Mar 2025        | -16.02% | 0.69 | -0.30  | 23.65%  |
| 5    | RSI      | BTC/USDT  | 15m | Jan-Mar 2025        | -24.31% | 0.51 | -0.45  | 25.73%  |
| 6    | CVD      | ETH/USDT  | 15m | Jan-Mar 2025        | -25.03% | 0.56 | -0.31  | 29.17%  |
| 7    | CVD      | BTC/USDT  | 15m | Jan-Mar 2025        | -28.10% | 0.14 | -0.62  | 29.88%  |
| 8    | CVD      | ETH/USDT  | 1h  | Jul 2024-Jan 2025   | -34.45% | 0.63 | -0.34  | 37.44%  |
| 9    | CVD      | BTC/USDT  | 1h  | Jul 2024-Jan 2025   | -37.61% | 0.52 | -0.51  | 39.56%  |
| 10   | RSI      | BTC/USDT  | 1h  | Jul 2024-Jan 2025   | -40.51% | 0.52 | -0.51  | 42.74%  |
| 11   | MACD     | BTC/USDT  | 1h  | Jul 2024-Jan 2025   | -92.92% | 0.56 | -1.53  | 93.25%  |
| 12   | MACD     | BTC/USDT  | 15m | Jan-Mar 2025        | -94.74% | 0.31 | -2.53  | 94.76%  |

---

## Analysis

### 1. No Strategy Demonstrates Consistent Profitability

Every single backtest across all 12 combinations produced a negative or flat return. Not a single run achieved a profit factor above 1.16, and only one (CVD on DOGE/USDT 1h) had a profit factor above 1.0 -- but with a return of effectively $0.02 on $1,000 capital. **None of these strategies are profitable in their current form.**

### 2. The CVD "Edge" Does Not Persist

CVD appeared promising in earlier tests, but the extended results tell a different story:

- **Across symbols (1h, Jan-Mar 2025):** CVD on SOL/USDT lost 3.87%, and on DOGE/USDT it was flat. The earlier perceived edge on BTC/USDT 1h does not generalize to other markets in a meaningful way.
- **Over longer periods (6 months, 1h):** CVD on BTC/USDT lost 37.61% and on ETH/USDT lost 34.45%. Over a longer time horizon, the strategy's losses compound dramatically. Whatever short-term edge existed in the 2-month window disappears entirely over 6 months.
- **On 15m timeframe:** CVD on BTC/USDT lost 28.10% and on ETH/USDT lost 25.03%. The 15m timeframe does not salvage performance.

**Conclusion: CVD has no durable edge.** The apparent short-term performance was likely noise or a favorable market regime that does not persist.

### 3. RSI Performs Poorly Everywhere

RSI produced losses across every combination tested:
- ETH/USDT 1h: -16.02%
- SOL/USDT 1h: -13.29%
- BTC/USDT 1h (6 months): -40.51%
- BTC/USDT 15m: -24.31%

Win rates ranged from 39% to 51%, with profit factors consistently well below 1.0. The strategy's losers are substantially larger than its winners in all cases.

### 4. MACD Is the Worst Performer

MACD is catastrophic in all tests:
- BTC/USDT 1h (6 months): -92.92% with 998 trades and a 26% win rate
- BTC/USDT 15m: -94.74% with 1,339 trades and a 20% win rate

MACD generates an extremely high number of trades with very low win rates. It is the most destructive strategy tested and appears to be overtrade-prone.

### 5. Timeframe Observations

- **1h timeframe** consistently produced fewer trades and smaller losses than 15m, suggesting less noise-driven whipsawing.
- **15m timeframe** increased trade count and generally worsened performance, likely due to more false signals in the higher-frequency data.
- The 1h timeframe is relatively less bad, but still not profitable.

### 6. Symbol Observations

- **DOGE/USDT** was the only symbol where any strategy broke even (CVD, +$0.02). This may be due to DOGE's lower absolute price making the fixed size=1 position trivially small.
- **BTC/USDT and ETH/USDT** consistently showed the largest dollar losses, as expected given their higher absolute prices.
- **SOL/USDT** showed moderate losses, falling between BTC/ETH and DOGE.

### 7. Key Structural Problem: Asymmetric Win/Loss Sizes

A recurring pattern across nearly all backtests: **average winners are much smaller than average losers**. For example:
- CVD BTC/USDT 1h (6mo): Avg winner $7.76, Avg loser -$21.08 (2.7x asymmetry)
- CVD ETH/USDT 1h (6mo): Avg winner $8.24, Avg loser -$21.94 (2.7x asymmetry)
- RSI BTC/USDT 1h (6mo): Avg winner $6.60, Avg loser -$11.30 (1.7x asymmetry)

This suggests the strategies are cutting winners short and letting losers run -- the opposite of sound risk management. Addressing this with better exit logic (trailing stops, profit targets, or improved stop-loss placement) would be the single most impactful improvement.

---

## Recommendations

1. **Do not deploy any of these strategies in their current form.** All are net losers.
2. **Focus on the win/loss asymmetry problem.** The CVD strategy achieves decent win rates (58-67%) but loses money because its losses are 2-3x larger than its wins. Better exit management could potentially flip this.
3. **Abandon MACD** in its current implementation. It generates excessive trades with abysmal win rates.
4. **If further development continues, use 1h timeframe** as the baseline -- it consistently outperforms 15m and (from earlier tests) 5m.
5. **Test with proper position sizing** relative to account equity rather than fixed size=1 to get more realistic return figures.
