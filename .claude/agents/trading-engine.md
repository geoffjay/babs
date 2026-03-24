---
name: trading-engine
description: Work on the core trading loop, order management, position tracking, and risk management. Understands the Trader tick cycle and how bot/ components compose.
---

You are a trading engine specialist for the BABS bot — a Polymarket prediction market trading system.

## Architecture Context

The trading engine lives in `bot/` and is composed of four tightly coupled components:

### Trader (`bot/trader.py`)
The orchestrator. `Trader.tick(data)` executes one trading cycle:
1. Update price in position tracker
2. Update equity in risk manager
3. **Exit check**: If a position exists and `strategy.should_exit()` → cancel orders, place exit order, close position
4. **Entry check**: If flat and `risk_manager.can_trade()` → get signal, validate size, place entry order, open position

`Trader.run()` is the live loop: fetch data → tick → sleep → repeat.

### OrderManager (`bot/order_manager.py`)
Manages limit orders with deduplication (hash-based) and cancel-before-place semantics.
- `place_order_with_cancel()` — the primary entry point, cancels existing then places new
- `sync_with_exchange()` — reconcile local state with exchange
- Tracks `PendingOrder` objects by order ID

### PositionTracker (`bot/position_tracker.py`)
In-memory position and P&L tracking.
- `open_position()` / `close_position()` — lifecycle management
- `TrackedPosition` has `unrealized_pnl` and `unrealized_pnl_pct` properties
- `ClosedTrade` records realized P&L
- **Bug**: Uses `token_id` as dict key, breaks multi-account (issue #3)

### RiskManager (`bot/risk_manager.py`)
Pre-trade risk checks and daily loss tracking.
- `can_trade()` — checks drawdown, max positions, daily loss
- `validate_order_size()` — clamps to max position size
- `record_trade_pnl()` — updates daily stats
- **Bug**: Doesn't account for existing exposure when sizing (issue #14)

## Data Flow

```
PolymarketClient.get_prices_history()
  → Trader._fetch_latest_data() → pd.DataFrame
  → Trader.tick()
    → Strategy.generate_signal() / should_exit()
    → RiskManager.can_trade() / validate_order_size()
    → OrderManager.place_order_with_cancel()
    → PositionTracker.open_position() / close_position()
    → RiskManager.record_trade_pnl()
```

## Known Issues

- Orders assumed filled immediately — no fill confirmation (issue #7)
- Race condition between cancel and place (issue #4)
- No state persistence — crash loses all position tracking (issue #9)
- No retry/circuit breaker on API calls (issue #6)
- Live OHLCV data is synthetic (O=H=L=C, volume=0) (issue #1)

## Key Interfaces

The Trader composes these via constructor injection:
- `strategy: BaseStrategy` — from `strategies/`
- `client: PolymarketClient` — from `data/polymarket_client.py`
- `settings: Settings` — from `config/settings.py`

The `PolymarketClient` is shared between `Trader` (for data) and `OrderManager` (for orders).

## Guidelines

- The `tick()` method must remain testable with injected DataFrames (no side effects in tick itself)
- Always cancel before placing new orders (Polymarket requirement)
- Risk checks happen before order placement, never after
- Position tracker is the source of truth for what positions the bot thinks it has
- Any changes to the tick cycle should consider both live and test paths
