"""The author's EMA-based Bill Williams research variant, not a textbook clone."""
from .common import inputs, signals, positive_int, finite


def generate(bars, *, threshold=0.001, ao_cross_window=20, provider=None):
    finite(threshold, "threshold")
    positive_int(ao_cross_window, "ao_cross_window")
    df, ind = inputs(bars, provider)
    high, low, close = df.high, df.low, df.close
    jaw = ind.ema(close, 13).shift(8)
    teeth = ind.ema(close, 8).shift(5)
    lips = ind.ema(close, 5).shift(3)
    median = (high + low) / 2
    ao = ind.ema(median, 5) - ind.ema(median, 34)
    ac = ao - ind.ema(ao, 5)
    peak = ((high.shift(1) > high) & (high.shift(2) > high.shift(1)) &
            (high.shift(2) > high.shift(3)) & (high.shift(3) > high.shift(4)))
    trough = ((low.shift(1) < low) & (low.shift(2) < low.shift(1)) &
              (low.shift(2) < low.shift(3)) & (low.shift(3) < low.shift(4)))
    # Confirmation uses a middle bar two bars in the past. No negative shifts.
    peak &= (high.shift(2) - high) / high > threshold
    trough &= (low - low.shift(2)) / low > threshold
    up = (ao > 0) & (ao.rolling(ao_cross_window).min() < 0)
    down = (ao < 0) & (ao.rolling(ao_cross_window).max() > 0)
    return signals(peak & (lips > teeth) & (teeth > jaw) & (close > lips) & (ac.diff() > 0) & up,
                   trough & (lips < teeth) & (teeth < jaw) & (close < lips) & (ac.diff() < 0) & down,
                   df.index)
