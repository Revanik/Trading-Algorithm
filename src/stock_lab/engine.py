"""Daily long/cash simulation with prior-close signals and next-open execution."""

import csv
import math
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class Bar:
    date: str
    symbol: str
    open: float
    close: float


@dataclass(frozen=True)
class Config:
    fast: int = 20
    slow: int = 100
    initial_cash: float = 10000.0
    max_exposure: float = 0.25
    cost_bps: float = 10.0
    max_drawdown: float = 0.10

    def __post_init__(self):
        if not 0 < self.fast < self.slow:
            raise ValueError("Require 0 < fast < slow")
        for name in ("initial_cash", "max_exposure", "cost_bps", "max_drawdown"):
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"{name} must be finite")
        if self.initial_cash <= 0 or not 0 < self.max_exposure <= 1:
            raise ValueError("Require positive cash and 0 < exposure <= 1")
        if not 0 <= self.cost_bps < 10000 or not 0 < self.max_drawdown < 1:
            raise ValueError("Invalid trading cost or drawdown limit")


def read_bars(path: Path) -> list[Bar]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if not {"date", "symbol", "open", "close"}.issubset(reader.fieldnames or []):
            raise ValueError("CSV requires date,symbol,open,close headers")
        bars = []
        for row in reader:
            try:
                day = date.fromisoformat(row["date"]).isoformat()
                symbol = row["symbol"].strip().upper()
                bar = Bar(day, symbol, float(row["open"]), float(row["close"]))
            except (ValueError, TypeError, AttributeError) as error:
                raise ValueError(
                    f"Invalid date, symbol, or price at CSV line {reader.line_num}"
                ) from error
            if not symbol or any(not math.isfinite(p) or p <= 0 for p in (bar.open, bar.close)):
                raise ValueError("Symbols must be nonempty; prices must be positive and finite")
            if bars and (bar.date <= bars[-1].date or bar.symbol != bars[-1].symbol):
                raise ValueError("Use one symbol, strictly increasing dates, and no duplicate rows")
            bars.append(bar)
    if not bars:
        raise ValueError("CSV contains no bars")
    return bars


def target(history: list[Bar], config: Config) -> float:
    if len(history) < config.slow:
        return 0.0
    fast = sum(b.close for b in history[-config.fast :]) / config.fast
    slow = sum(b.close for b in history[-config.slow :]) / config.slow
    return config.max_exposure if fast > slow else 0.0


def simulate(bars: list[Bar], config: Config, start: str | None = None) -> dict:
    """Recompute deterministically; earlier bars only warm up signals before start."""
    if start:
        start = date.fromisoformat(start).isoformat()
    first = next((i for i, bar in enumerate(bars) if not start or bar.date >= start), None)
    if first is None:
        raise ValueError("No data on or after evaluation start")
    cash = config.initial_cash
    shares = 0
    peak = config.initial_cash
    halted = False
    fills = []
    curve = []
    cost_rate = config.cost_bps / 10000
    for i in range(first, len(bars)):
        bar = bars[i]
        allocation = 0.0 if halted else target(bars[:i], config)
        open_equity = cash + shares * bar.open
        # Solve for allocation of equity after costs on the actual traded quantity.
        current_value = shares * bar.open
        if current_value <= open_equity * allocation:
            budget = allocation * (open_equity + cost_rate * current_value)
            denominator = bar.open * (1 + allocation * cost_rate)
        else:
            budget = allocation * (open_equity - cost_rate * current_value)
            denominator = bar.open * (1 - allocation * cost_rate)
        desired = math.floor(budget / denominator)
        delta = desired - shares
        if delta > 0:
            delta = min(delta, math.floor(cash / (bar.open * (1 + cost_rate))))
        if delta:
            cost = abs(delta) * bar.open * cost_rate
            cash -= delta * bar.open + cost
            shares += delta
            fills.append(
                {
                    "date": bar.date,
                    "symbol": bar.symbol,
                    "shares": delta,
                    "price": bar.open,
                    "cost": cost,
                }
            )
        equity = cash + shares * bar.close
        peak = max(peak, equity)
        drawdown = 1 - equity / peak
        # Latch permanently for this run; liquidation happens at the next available open.
        halted = halted or drawdown >= config.max_drawdown
        curve.append(
            {
                "date": bar.date,
                "cash": cash,
                "shares": shares,
                "equity": equity,
                "drawdown": drawdown,
                "halted": halted,
            }
        )
    return {
        "mode": "local_simulation",
        "symbol": bars[0].symbol,
        "config": asdict(config),
        "evaluation_start": bars[first].date,
        "last_date": bars[-1].date,
        "total_return": curve[-1]["equity"] / config.initial_cash - 1,
        "max_drawdown": max(row["drawdown"] for row in curve),
        "buy_hold_return_before_costs": bars[-1].close / bars[first].open - 1,
        "fill_count": len(fills),
        "total_cost": sum(fill["cost"] for fill in fills),
        "halted": halted,
        "fills": fills,
        "equity_curve": curve,
    }
