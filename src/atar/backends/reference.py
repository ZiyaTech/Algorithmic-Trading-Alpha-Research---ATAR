"""Small fixed-notional OHLC simulator with explicit, conservative fill rules.

Completed-bar decisions enter at the next bar's open. One position, no leverage,
no pyramiding, no trailing stops. Existing-position gaps fill at the open.
If stop and target both touch, the stop wins. Window-end exits use its last
close. This is not tick replay, broker netting or the private IH engine.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math
import numpy as np
from atar.temporal import Window, validate_ohlc
from atar.strategies.common import Signals


@dataclass(frozen=True)
class Execution:
    stop_loss: float = 0.012
    take_profit: float = 0.018
    cost_bps_per_side: float = 2.0
    max_holding_bars: int = 24

    def __post_init__(self):
        for k in ("stop_loss", "take_profit"):
            v = getattr(self, k)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 < v < 1:
                raise ValueError(f"{k} must be in (0,1)")
        if (isinstance(self.cost_bps_per_side, bool) or
            not isinstance(self.cost_bps_per_side, (int, float)) or
            not math.isfinite(self.cost_bps_per_side) or not 0 <= self.cost_bps_per_side < 10000):
            raise ValueError("Invalid costs")
        if type(self.max_holding_bars) is not int or self.max_holding_bars < 1:
            raise ValueError("max_holding_bars must be a positive integer")


@dataclass(frozen=True)
class Trade:
    entry_time: str
    exit_bar_time: str
    side: int
    entry_price: float
    exit_price: float
    net_return: float
    exit_reason: str


def summarize(trades: list[Trade], equity: list[float]) -> dict:
    r = np.array([t.net_return for t in trades])
    gains = float(r[r > 0].sum())
    losses = float(-r[r < 0].sum())
    pf = gains / losses if losses else ("+inf" if gains > 0 else None)
    curve = np.array([0.0, *equity])
    dd = np.maximum.accumulate(curve) - curve
    return {"trades_count": len(trades), "fixed_notional_return": float(r.sum()),
            "mean_trade_return": float(r.mean()) if len(r) else None,
            "win_rate": float((r > 0).mean()) if len(r) else None,
            "profit_factor": pf, "max_drawdown_fixed_notional": float(dd.max())}


def simulate(bars, entry_signals: Signals, window: Window, execution: Execution) -> dict:
    data = validate_ohlc(bars)
    entry_signals.validate(data.index)
    dt = data.index[1] - data.index[0]
    if window.start < data.index[0] or window.end > data.index[-1] + dt:
        raise ValueError("Window is not fully covered by supplied bars")
    if window.start not in data.index or (window.end != data.index[-1] + dt and window.end not in data.index):
        raise ValueError("Window boundaries must align to bar opens")
    positions = np.flatnonzero((data.index >= window.start) & (data.index < window.end))
    if len(positions) < 2:
        raise ValueError("Evaluation requires at least two complete bars")
    o, h, l, c = (data[k].to_numpy() for k in ("open", "high", "low", "close"))
    long, short = entry_signals.long.to_numpy(), entry_signals.short.to_numpy()
    trades, equity = [], []
    side, start, entry, stop, target = 0, 0, 0.0, 0.0, 0.0
    realized = 0.0
    fee = execution.cost_bps_per_side / 10000
    first, last = int(positions[0]), int(positions[-1])
    for i in positions:
        was_open = side != 0
        if not was_open and i > first:
            # Training/earlier-window decisions cannot open a new stage position.
            side = 1 if long[i - 1] else (-1 if short[i - 1] else 0)
            if side:
                start, entry = int(i), float(o[i])
                stop = entry * (1 - side * execution.stop_loss)
                target = entry * (1 + side * execution.take_profit)
        fill, reason = None, ""
        if side:
            if was_open and ((side == 1 and o[i] <= stop) or (side == -1 and o[i] >= stop)):
                fill, reason = float(o[i]), "gap_stop"
            elif was_open and ((side == 1 and o[i] >= target) or (side == -1 and o[i] <= target)):
                fill, reason = float(o[i]), "gap_target"
            elif (side == 1 and l[i] <= stop) or (side == -1 and h[i] >= stop):
                fill, reason = stop, "stop"
            elif (side == 1 and h[i] >= target) or (side == -1 and l[i] <= target):
                fill, reason = target, "target"
            elif int(i) - start + 1 >= execution.max_holding_bars:
                fill, reason = float(c[i]), "holding_limit"
            elif i == last:
                fill, reason = float(c[i]), "window_end"
            if fill is not None:
                net = side * (fill - entry) / entry - 2 * fee
                trades.append(Trade(data.index[start].isoformat(), data.index[i].isoformat(),
                                    side, entry, fill, float(net), reason))
                realized += net
                side = 0
        equity.append(float(realized + (side * (c[i] - entry) / entry - fee if side else 0.0)))
    return {"metrics": summarize(trades, equity), "trades": [asdict(t) for t in trades],
            "bars_evaluated": len(positions)}
