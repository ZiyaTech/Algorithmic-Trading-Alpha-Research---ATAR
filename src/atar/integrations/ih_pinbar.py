"""Standalone extraction of the IH PinBarEMARSI quote-to-completed-bar path.

Preserves new-bar gating, first-tick initialization, strict crossover resets,
trading-hour filtering, open-position suppression and bid/ask order-level math.
Private TradingStrategy, account sizing, broker submission, signal inversion and
operational identifiers are deliberately not imported. Returns OrderIntent.
"""
from __future__ import annotations
from dataclasses import dataclass
import threading
import pandas as pd
from atar.temporal import validate_ohlc, utc
from atar.indicators import ReferenceIndicators
from atar.strategies.pinbar_emarsi_ih import check_pinbar, update_rsi_flags, check_signals
from atar.strategies.common import finite, positive_int


@dataclass(frozen=True)
class OrderIntent:
    timestamp: pd.Timestamp
    side: str
    entry_price: float
    stop_loss: float
    take_profit: float
    trailing_distance: float | None


class PinBarEMARSIStrategy:
    """Research callback adapter. Caller owns fills and open-position state.

    Prepared bars are UTC and bar-open-labelled. Precomputed indicators are read
    only at the previous completed bar and its predecessor. With provider=None,
    use the independent reference indicators; VBTProIndicators is optional.
    """
    def __init__(self, bars, *, tail_ratio_threshold, ema_short_period, ema_long_period,
                 stop_loss_ratio, take_profit_ratio, trailing_stop_ratio=None,
                 rsi_period=14, rsi_overbought=80.0, rsi_oversold=20.0,
                 start_hour=0, end_hour=24, provider=None):
        finite(tail_ratio_threshold, "tail_ratio_threshold", 0, 1)
        for value in (ema_short_period, ema_long_period, rsi_period):
            positive_int(value, "indicator period", 2)
        if ema_short_period >= ema_long_period:
            raise ValueError("EMA periods must be ordered")
        for value in (stop_loss_ratio, take_profit_ratio):
            finite(value, "exit ratio", 0, 1)
            if value == 0 or value == 1:
                raise ValueError("Exit ratios must be in (0,1)")
        if trailing_stop_ratio is not None:
            finite(trailing_stop_ratio, "trailing_stop_ratio", 0, 1)
            if trailing_stop_ratio in (0, 1):
                raise ValueError("Trailing ratio must be in (0,1) or None")
        if type(start_hour) is not int or type(end_hour) is not int or not 0 <= start_hour < end_hour <= 24:
            raise ValueError("Trading hours must satisfy 0 <= start < end <= 24")
        finite(rsi_oversold, "rsi_oversold", 0, 100)
        finite(rsi_overbought, "rsi_overbought", 0, 100)
        if rsi_oversold >= rsi_overbought:
            raise ValueError("RSI bands must be ordered")
        self.bars = validate_ohlc(bars)
        self.delta = self.bars.index[1] - self.bars.index[0]
        self.ratio, self.sl, self.tp, self.ts = tail_ratio_threshold, stop_loss_ratio, take_profit_ratio, trailing_stop_ratio
        self.start_hour, self.end_hour = start_hour, end_hour
        self.overbought, self.oversold = rsi_overbought, rsi_oversold
        ind = provider if provider is not None else ReferenceIndicators()
        self.fast = ind.ema(self.bars.close, ema_short_period)
        self.slow = ind.ema(self.bars.close, ema_long_period)
        self.rsi = ind.rsi(self.bars.close, rsi_period)
        self.last_processed_bar_time = None
        self.rsi_up_flag = self.rsi_down_flag = False
        self.lock = threading.Lock()

    def on_quote_tick(self, timestamp, *, bid, ask, has_open_order=False):
        timestamp = utc(timestamp)
        finite(bid, "bid")
        finite(ask, "ask")
        if bid <= 0 or ask <= 0 or bid > ask:
            raise ValueError("Require 0 < bid <= ask")
        if type(has_open_order) is not bool:
            raise ValueError("has_open_order must be boolean")
        if not self.start_hour <= timestamp.hour < self.end_hour:
            return None
        current = timestamp.floor(self.delta)
        with self.lock:
            if self.last_processed_bar_time is None:
                self.last_processed_bar_time = current
                return None
            if current <= self.last_processed_bar_time:
                return None
            self.last_processed_bar_time = current
            previous, before = current - self.delta, current - 2 * self.delta
            if previous not in self.bars.index or before not in self.bars.index:
                return None
            bar = self.bars.loc[previous]
            fast, slow = self.fast.loc[previous], self.slow.loc[previous]
            bullish, bearish = check_pinbar(bar.high, bar.low, bar.close, bar.open, self.ratio)
            self.rsi_up_flag, self.rsi_down_flag = update_rsi_flags(
                fast, slow, self.fast.loc[before], self.slow.loc[before], self.rsi.loc[previous],
                self.rsi_up_flag, self.rsi_down_flag, self.overbought, self.oversold)
            buy, sell = check_signals(fast, slow, bar.high, bar.low, bullish, bearish,
                                      self.rsi_up_flag, self.rsi_down_flag, 0)
            if has_open_order or not (buy or sell):
                return None
            if buy:
                return OrderIntent(timestamp, "BUY", ask, bid * (1 - self.sl), ask * (1 + self.tp),
                                   None if self.ts is None else bid * self.ts)
            return OrderIntent(timestamp, "SELL", bid, ask * (1 + self.sl), bid * (1 - self.tp),
                               None if self.ts is None else ask * self.ts)
