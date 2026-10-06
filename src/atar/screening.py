"""Illustrative, caller-controlled gates. No production selection rules."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math


@dataclass(frozen=True)
class Gate:
    min_trades: int = 1
    min_return: float | None = None
    min_profit_factor: float | None = None

    def __post_init__(self):
        if type(self.min_trades) is not int or self.min_trades < 0:
            raise ValueError("min_trades must be a nonnegative integer")
        for value in (self.min_return, self.min_profit_factor):
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise ValueError("Gate thresholds must be finite numbers or null")
        if self.min_profit_factor is not None and self.min_profit_factor < 0:
            raise ValueError("Profit factor threshold cannot be negative")

    def as_dict(self):
        return asdict(self)

    def decide(self, metrics: dict) -> tuple[bool, list[str]]:
        rules = [("trades_count", self.min_trades, False),
                 ("fixed_notional_return", self.min_return, False),
                 ("profit_factor", self.min_profit_factor, True)]
        reasons = []
        for key, bound, allow_positive_inf in rules:
            if bound is None:
                continue
            if key not in metrics:
                raise ValueError(f"Required metric missing: {key}")
            raw = metrics[key]
            try:
                value = float(raw) if not isinstance(raw, bool) else float("nan")
            except (TypeError, ValueError):
                value = float("nan")
            valid = math.isfinite(value) or (allow_positive_inf and value == math.inf)
            if key == "trades_count":
                valid = valid and value >= 0 and value.is_integer()
            if not valid:
                reasons.append(f"{key}:undefined")
            elif value < bound:
                reasons.append(f"{key}:below_threshold")
        return not reasons, reasons
