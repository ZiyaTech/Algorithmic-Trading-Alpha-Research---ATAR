"""Author's vectorized PinBarEMARSI API, preserving minute/timeframe alignment.

This optional integration keeps the original VBT Pro indicator calls and
minute-bar signal mapping. The package's completed-bar reference variant is
separate. Input must be a regular, UTC, bar-open-labelled minute series.
Returns executable-time masks as the original API did, NOT close-time masks.
Do not pass these masks to ReferenceBackend, which expects close-time decisions.
"""
import numpy as np
import pandas as pd
from atar.temporal import validate_ohlc


def pinbaremarsi_signal(o, h, l, c, timeframe, pinbar_ratio, bt_period, trading_time,
                        fast_ema_period=20, slow_ema_period=50, rsi_period=14):
    import vectorbtpro as vbt
    df = validate_ohlc(pd.DataFrame({"open": o, "high": h, "low": l, "close": c}))
    if df.index[1] - df.index[0] != pd.Timedelta(minutes=1):
        raise ValueError("Original vectorized API requires one-minute input bars")
    if not 0 <= pinbar_ratio <= 1:
        raise ValueError("pinbar_ratio must be in [0, 1]")
    EMA, RSI = vbt.indicator("talib:EMA"), vbt.indicator("talib:RSI")
    fast = EMA.run(df.close, timeperiod=fast_ema_period, timeframe=timeframe, skipna=True,
                   wrapper_kwargs={"freq": "1min"}).real
    slow = EMA.run(df.close, timeperiod=slow_ema_period, timeframe=timeframe, skipna=True,
                   wrapper_kwargs={"freq": "1min"}).real
    rsi = RSI.run(df.close, timeperiod=rsi_period, timeframe=timeframe, skipna=True,
                  wrapper_kwargs={"freq": "1min"}).real
    state = pd.Series(np.nan, index=rsi.index)
    state[rsi > 80], state[rsi < 20] = 1, -1
    sign = pd.Series(np.where(fast - slow > 0, 2, -2), index=df.index)
    state[(sign == 2) & (sign.shift() == -2)] = 2
    state[(sign == -2) & (sign.shift() == 2)] = -2
    state = state.ffill()
    sampled = df if timeframe == "1min" else df.resample(timeframe).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"})
    width = (sampled.high - sampled.low).abs()
    bullish = ((sampled[["open", "close"]].min(axis=1) - sampled.low >= pinbar_ratio * width)
               & (sampled.close > sampled.open))
    bearish = ((sampled.high - sampled[["open", "close"]].max(axis=1) >= pinbar_ratio * width)
               & (sampled.close < sampled.open))

    def map_bars(condition, values):
        selected = sampled.loc[condition]
        indices = np.searchsorted(df.index, selected.index + pd.Timedelta(timeframe), side="left")
        valid = indices < len(df)
        mask = pd.Series(False, index=df.index)
        levels = pd.Series(np.nan, index=df.index)
        mask.iloc[indices[valid]] = True
        levels.iloc[indices[valid]] = selected[values].to_numpy()[valid]
        return mask, levels

    bullish_mask, pin_low = map_bars(bullish, "low")
    bearish_mask, pin_high = map_bars(bearish, "high")
    long = bullish_mask & (fast > slow) & (pin_low < fast) & (state == 1)
    short = bearish_mask & (fast < slow) & (pin_high > fast) & (state == -1)
    idx = df.loc[bt_period[0]:bt_period[1]].index
    allowed = ((idx.time >= pd.to_datetime(trading_time[0]).time()) &
               (idx.time <= pd.to_datetime(trading_time[1]).time()))
    return long.loc[idx] & allowed, None, short.loc[idx] & allowed, None
