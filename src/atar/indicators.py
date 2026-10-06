"""Independent reference indicators and a lazy, optional VBT Pro adapter."""
from __future__ import annotations
from typing import Protocol
import numpy as np
import pandas as pd


def period_check(period: int) -> None:
    if type(period) is not int or period < 2:
        raise ValueError("Indicator period must be an integer >= 2")


class Indicators(Protocol):
    def ema(self, series: pd.Series, period: int) -> pd.Series: ...
    def rsi(self, series: pd.Series, period: int) -> pd.Series: ...


class ReferenceIndicators:
    """SMA-seeded EMA and Wilder RSI. NaNs restart a contiguous warmup."""
    name = "reference-indicators-v1"

    def ema(self, series, period):
        period_check(period)
        x = np.asarray(series, dtype=float)
        out = np.full(len(x), np.nan)
        buffer, last = [], np.nan
        for i, value in enumerate(x):
            if not np.isfinite(value):
                buffer, last = [], np.nan
                continue
            if np.isnan(last):
                buffer.append(value)
                if len(buffer) == period:
                    last = float(np.mean(buffer))
                    out[i] = last
            else:
                last += (2.0 / (period + 1)) * (value - last)
                out[i] = last
        return pd.Series(out, index=series.index)

    def rsi(self, series, period):
        period_check(period)
        x = np.asarray(series, dtype=float)
        out = np.full(len(x), np.nan)
        gain = loss = 0.0
        count = 0
        for i in range(1, len(x)):
            if not np.isfinite(x[i - 1:i + 1]).all():
                gain = loss = 0.0
                count = 0
                continue
            delta = x[i] - x[i - 1]
            up, down = max(delta, 0.0), max(-delta, 0.0)
            if count < period:
                gain += up / period
                loss += down / period
                count += 1
            else:
                gain = ((period - 1) * gain + up) / period
                loss = ((period - 1) * loss + down) / period
            if count >= period:
                out[i] = 100 * gain / (gain + loss) if gain + loss > 0 else 0.0
        return pd.Series(out, index=series.index)


class VBTProIndicators:
    """Calls the user's separately installed vectorbtpro dependency; no vendor code."""
    name = "vbtpro-talib-indicators"

    def __init__(self):
        try:
            import vectorbtpro as vbt
        except ImportError as exc:
            raise ImportError("Install your licensed vectorbtpro environment separately, or use reference indicators") from exc
        self._ema = vbt.indicator("talib:EMA")
        self._rsi = vbt.indicator("talib:RSI")
        self.version = getattr(vbt, "__version__", "unknown")

    def ema(self, series, period):
        period_check(period)
        return self._ema.run(series, timeperiod=period, skipna=True).real.reindex(series.index)

    def rsi(self, series, period):
        period_check(period)
        return self._rsi.run(series, timeperiod=period, skipna=True).real.reindex(series.index)
