"""Bot settings: position size, timeframes, risk parameters, strategy defaults."""

from dataclasses import dataclass, field


@dataclass
class MACDParams:
    fast: int = 3
    slow: int = 15
    signal: int = 3


@dataclass
class RSIParams:
    period: int = 14
    oversold: float = 30.0
    overbought: float = 70.0


@dataclass
class CVDParams:
    lookback: int = 20
    divergence_threshold: float = 0.01


@dataclass
class RiskParams:
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.10
    max_drawdown: float = 0.20
    max_open_positions: int = 3
    max_daily_loss: float = 50.0
    max_position_size: float = 100.0


@dataclass
class Settings:
    position_size: float = 1.0
    timeframe: str = "5m"
    poll_interval_seconds: int = 30

    # Polymarket CLOB connection
    clob_host: str = "https://clob.polymarket.com"
    chain_id: int = 137
    signature_type: int = 2

    # Strategy parameters
    macd: MACDParams = field(default_factory=MACDParams)
    rsi: RSIParams = field(default_factory=RSIParams)
    cvd: CVDParams = field(default_factory=CVDParams)

    # Risk management
    risk: RiskParams = field(default_factory=RiskParams)


DEFAULT_SETTINGS = Settings()
