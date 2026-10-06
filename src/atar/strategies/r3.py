"""RSI directional streaks in the context of an EMA trend filter."""
from .common import inputs, signals, positive_int


def generate(bars, *, rsi_period=2, rsi_streak_bars=3, ema_period=120, provider=None):
    positive_int(rsi_period, "rsi_period", 2)
    positive_int(rsi_streak_bars, "rsi_streak_bars")
    positive_int(ema_period, "ema_period", 2)
    df, ind = inputs(bars, provider)
    rsi, ema = ind.rsi(df.close, rsi_period), ind.ema(df.close, ema_period)
    up = (rsi.diff() > 0).astype(int)
    down = (rsi.diff() < 0).astype(int)
    up_count = up.groupby((up != up.shift()).cumsum()).cumsum()
    down_count = down.groupby((down != down.shift()).cumsum()).cumsum()
    return signals((df.close > ema) & (rsi.shift(rsi_streak_bars - 1) < 60) &
                   (down_count >= rsi_streak_bars) & (rsi < 10),
                   (df.close < ema) & (rsi.shift(rsi_streak_bars - 1) > 40) &
                   (up_count >= rsi_streak_bars) & (rsi > 90), df.index)
