"""Signals are decisions at a completed bar's close, not same-bar fills."""
from __future__ import annotations
from dataclasses import dataclass
import math
import pandas as pd
from atar.indicators import ReferenceIndicators
from atar.temporal import validate_ohlc


@dataclass(frozen=True)
class Signals:
    long: pd.Series
    short: pd.Series

    def validate(self, index: pd.Index):
        for side in (self.long, self.short):
            if not isinstance(side, pd.Series) or not side.index.equals(index):
                raise ValueError("Signal index must exactly match bars")
            if side.isna().any() or side.dtype != bool:
                raise ValueError("Signals must be boolean, without missing values")
        if (self.long & self.short).any():
            raise ValueError("Simultaneous long/short decisions are not supported")
        return self


def signals(long, short, index):
    return Signals(pd.Series(long, index=index).fillna(False).astype(bool),
                   pd.Series(short, index=index).fillna(False).astype(bool)).validate(index)


def inputs(bars, provider):
    return validate_ohlc(bars), provider if provider is not None else ReferenceIndicators()


def positive_int(value, label, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label} must be an integer >= {minimum}")


def finite(value, label, low=0.0, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be finite")
    if value < low or (high is not None and value > high):
        raise ValueError(f"{label} outside supported range")
