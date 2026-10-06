"""Serialized, IH-derived PinBarEMARSI state machine for completed-bar research.

The three decision helpers retain the source inequalities and flag transitions.
Broker submission, private base-class coupling and deployment metadata are not
part of this extraction. This is runnable research code, not the private IH
execution engine. See docs/pinbar_variants.md for the callback adaptation.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from .common import inputs, signals, positive_int, finite


def check_pinbar(high, low, close, open_price, tail_ratio_threshold):
    upper_tail = high - max(open_price, close)
    lower_tail = min(open_price, close) - low
    total_range = high - low
    if total_range == 0:
        return False, False
    return ((lower_tail / total_range > tail_ratio_threshold) and (open_price < close),
            (upper_tail / total_range > tail_ratio_threshold) and (close < open_price))


def update_rsi_flags(ema_short_last, ema_long_last, ema_short_prev, ema_long_prev,
                     rsi, rsi_up_flag, rsi_down_flag, rsi_overbought, rsi_oversold):
    ema_cross_up = (ema_short_last > ema_long_last) and (ema_short_prev < ema_long_prev)
    ema_cross_down = (ema_short_last < ema_long_last) and (ema_short_prev > ema_long_prev)
    if rsi > rsi_overbought:
        rsi_up_flag, rsi_down_flag = True, False
    elif rsi < rsi_oversold:
        rsi_up_flag, rsi_down_flag = False, True
    if ema_cross_up or ema_cross_down:
        rsi_up_flag = rsi_down_flag = False
    return rsi_up_flag, rsi_down_flag


def check_signals(ema_short_last, ema_long_last, high, low, is_bullish_pinbar,
                  is_bearish_pinbar, rsi_up_flag, rsi_down_flag, current_position):
    buy = (ema_short_last > ema_long_last and rsi_up_flag and is_bullish_pinbar
           and low < ema_short_last and current_position != 1)
    sell = (ema_short_last < ema_long_last and rsi_down_flag and is_bearish_pinbar
            and high > ema_short_last and current_position != -1)
    return buy, sell


@dataclass
class SignalState:
    rsi_up_flag: bool = False
    rsi_down_flag: bool = False
    previous_fast: float = float("nan")
    previous_slow: float = float("nan")
    last_bar: pd.Timestamp | None = None


class PinBarEMARSISerialized:
    """One event per completed bar; no account access or order side effects.

    Caller-supplied indicators must be known by the bar's close. Decisions are
    returned at that close and are executable no earlier than the next bar.
    Duplicate callbacks are ignored; out-of-order callbacks are rejected.
    """
    def __init__(self, *, pinbar_ratio=0.65, rsi_overbought=80.0, rsi_oversold=20.0):
        finite(pinbar_ratio, "pinbar_ratio", 0.0, 1.0)
        finite(rsi_overbought, "rsi_overbought", 0.0, 100.0)
        finite(rsi_oversold, "rsi_oversold", 0.0, 100.0)
        if rsi_oversold >= rsi_overbought:
            raise ValueError("RSI bands must be ordered")
        self.ratio = pinbar_ratio
        self.overbought, self.oversold = rsi_overbought, rsi_oversold
        self.state = SignalState()

    def on_completed_bar(self, timestamp, bar, *, ema_fast, ema_slow, rsi,
                         current_position=0):
        timestamp = pd.Timestamp(timestamp)
        if timestamp.tzinfo is None or pd.isna(timestamp):
            raise ValueError("Timezone-aware bar timestamp required")
        s = self.state
        if s.last_bar is not None:
            if timestamp < s.last_bar:
                raise ValueError("Out-of-order bar")
            if timestamp == s.last_bar:
                return False, False
        if current_position not in (-1, 0, 1):
            raise ValueError("Position must be -1, 0 or 1")
        bullish, bearish = check_pinbar(bar['high'], bar['low'], bar['close'], bar['open'], self.ratio)
        up, down = update_rsi_flags(ema_fast, ema_slow, s.previous_fast, s.previous_slow,
                                    rsi, s.rsi_up_flag, s.rsi_down_flag, self.overbought, self.oversold)
        result = check_signals(ema_fast, ema_slow, bar['high'], bar['low'], bullish, bearish,
                               up, down, current_position)
        s.rsi_up_flag, s.rsi_down_flag = bool(up), bool(down)
        s.previous_fast, s.previous_slow, s.last_bar = ema_fast, ema_slow, timestamp
        return bool(result[0]), bool(result[1])


def generate(bars, *, pinbar_ratio=0.65, fast_ema_period=20, slow_ema_period=50,
             rsi_period=14, provider=None):
    for value in (fast_ema_period, slow_ema_period, rsi_period):
        positive_int(value, "indicator period", 2)
    if fast_ema_period >= slow_ema_period:
        raise ValueError("fast_ema_period must be smaller than slow_ema_period")
    df, ind = inputs(bars, provider)
    fast = ind.ema(df.close, fast_ema_period).to_numpy()
    slow = ind.ema(df.close, slow_ema_period).to_numpy()
    rsi = ind.rsi(df.close, rsi_period).to_numpy()
    machine = PinBarEMARSISerialized(pinbar_ratio=pinbar_ratio)
    long = np.zeros(len(df), dtype=bool)
    short = np.zeros(len(df), dtype=bool)
    # Indicators are causal. The state transition itself is strictly sequential.
    for i, (timestamp, row) in enumerate(df.iterrows()):
        long[i], short[i] = machine.on_completed_bar(timestamp, row, ema_fast=fast[i],
                                                     ema_slow=slow[i], rsi=rsi[i])
    return signals(long, short, df.index)
