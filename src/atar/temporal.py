"""Half-open evaluation windows and strict, regularly spaced UTC OHLC input."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import numpy as np
import pandas as pd


def utc(value) -> pd.Timestamp:
    t = pd.Timestamp(value)
    if pd.isna(t) or t.tzinfo is None:
        raise ValueError("Timestamps must be explicit and timezone-aware")
    return t.tz_convert("UTC")


@dataclass(frozen=True)
class Window:
    name: str
    start: pd.Timestamp
    end: pd.Timestamp

    def __post_init__(self):
        object.__setattr__(self, "start", utc(self.start))
        object.__setattr__(self, "end", utc(self.end))
        if not self.name or self.start >= self.end:
            raise ValueError("Window must have a name and start < end")

    def as_dict(self):
        return {"name": self.name, "start": self.start.isoformat(), "end_exclusive": self.end.isoformat()}


@dataclass(frozen=True)
class Fold:
    train: Window
    validation: Window
    final: Window

    def __post_init__(self):
        if not (self.train.end <= self.validation.start < self.validation.end <= self.final.start):
            raise ValueError("Fold windows overlap or are out of temporal order")
        if len({self.train.name, self.validation.name, self.final.name}) != 3:
            raise ValueError("Fold window names must be unique")


def validate_ohlc(frame: pd.DataFrame) -> pd.DataFrame:
    cols = ["open", "high", "low", "close"]
    if not isinstance(frame, pd.DataFrame) or not set(cols).issubset(frame):
        raise ValueError("OHLC columns are required")
    idx = frame.index
    if not isinstance(idx, pd.DatetimeIndex) or idx.tz is None:
        raise ValueError("OHLC index must be timezone-aware")
    if len(frame) < 2 or idx.hasnans or idx.has_duplicates or not idx.is_monotonic_increasing:
        raise ValueError("OHLC needs >=2 ordered, unique timestamps")
    step = np.diff(idx.asi8)
    if not (step > 0).all() or not (step == step[0]).all():
        raise ValueError("Reference backend requires regular bars; do not silently fill gaps")
    out = frame[cols].astype(float).copy()
    out.index = idx.tz_convert("UTC")
    x = out.to_numpy()
    if not np.isfinite(x).all() or (x <= 0).any():
        raise ValueError("OHLC prices must be finite and positive")
    if ((out.high < out[["open", "close", "low"]].max(axis=1)) |
        (out.low > out[["open", "close", "high"]].min(axis=1))).any():
        raise ValueError("Inconsistent OHLC bounds")
    return out


def data_digest(frame: pd.DataFrame) -> str:
    data = validate_ohlc(frame)
    h = hashlib.sha256()
    # Normalize resolution: asi8 is expressed in the index's unit, not always ns.
    h.update(data.index.as_unit("ns").asi8.astype("<i8").tobytes())
    h.update(data.to_numpy().astype("<f8").tobytes())
    return h.hexdigest()


def complete_bars(frame: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Resample bar-open-labelled data, dropping any incomplete aggregate bar."""
    data = validate_ohlc(frame)
    base = data.index[1] - data.index[0]
    target = pd.Timedelta(timeframe)
    if target < base or target % base:
        raise ValueError("Target timeframe must be an integer multiple of input bars")
    n = int(target / base)
    grouped = data.resample(timeframe, origin="epoch", label="left", closed="left")
    result = grouped.agg({"open": "first", "high": "max", "low": "min", "close": "last"})
    return result.loc[grouped["close"].count() == n]


def rolling_folds(index: pd.DatetimeIndex, *, warmup: int, train: int,
                  validation: int, final: int, step: int) -> list[Fold]:
    """Rolling fold specification, requiring non-overlapping final intervals."""
    sizes = (warmup, train, validation, final, step)
    if any(type(x) is not int or x <= 0 for x in sizes) or step < final:
        raise ValueError("Positive lengths and step >= final are required")
    if (not isinstance(index, pd.DatetimeIndex) or len(index) < 2 or index.tz is None
            or index.hasnans or index.has_duplicates or not index.is_monotonic_increasing):
        raise ValueError("Ordered timezone-aware index required")
    delta = index[1] - index[0]
    # Compare like units. Pandas indices may store seconds, ms, us or ns.
    deltas = np.diff(index.asi8)
    if not (deltas > 0).all() or not (deltas == deltas[0]).all():
        raise ValueError("Regular index required")
    edges = index.append(pd.DatetimeIndex([index[-1] + delta]))
    folds = []
    for start in range(warmup, len(index) - train - validation - final + 1, step):
        a, b, c, d = start, start + train, start + train + validation, start + train + validation + final
        folds.append(Fold(Window("train", edges[a], edges[b]),
                          Window("validation", edges[b], edges[c]),
                          Window("final", edges[c], edges[d])))
    if not folds:
        raise ValueError("Not enough bars for the declared fold")
    return folds
