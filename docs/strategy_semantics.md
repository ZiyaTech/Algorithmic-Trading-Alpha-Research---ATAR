# Strategy semantics

The five selected families are educational research implementations, not claims of profitable signals. Parameters in the example were authored for this demonstration rather than exported from a selected trading inventory.

All core generators consume complete, bar-open-labelled OHLC and return decisions known at that bar's close. The reference backend shifts execution to the next open. Indicators warm up on available historical bars. Neither strategy nor indicator code should use a negative shift or future aggregate.

| Name | Conditions retained | Important qualification |
|---|---|---|
| PinBarEMARSI | Tail geometry, candle direction, EMA order, price crossing the fast EMA, latched RSI state | Vectorized tail uses `>=`. IH helper uses strict `>`. Crossover equality treatment differs. |
| RainbowEMA | A 22-period ribbon, historical ribbon ordering, pullback level and current fastest-EMA slope | This is not reduced to a two-EMA crossover. Ribbon periods are formula constants, not a selected parameter record. |
| BillWilliams | Shifted EMA lines, EMA-based AO/AC, delayed fractal confirmation and zero-cross context | The author's EMA-based research variant. Not a claim of complete canonical Profitunity rules. |
| TrendScore | Seven historical comparisons, smoothed score, EMA order, price breakout and three-candle geometry | The three bodies are compared against the current slow EMA, matching the extracted formula. |
| R3 | RSI direction streaks, initial RSI condition, extreme RSI threshold and EMA context | The author's RSI-streak/EMA variant. No claim that another R3 implementation is identical. |

## Indicator providers

The default provider independently implements SMA-seeded EMA and Wilder RSI. A fully flat RSI warmup yields zero. Non-finite input interrupts the contiguous indicator warmup. These choices are visible in `indicators.py` and hand-checked in tests.

`VBTProIndicators` calls `vectorbtpro.indicator("talib:EMA")` and its RSI counterpart on already completed bars. It is optional. A reference implementation is not declared vendor-equivalent without a licensed-runtime comparison covering initialization, missing values and alignment.

## No hidden timeframe remapping

Core generators operate on the timeframe supplied. Use `complete_bars` before generation to aggregate a regular lower-frequency series. The special original VBT PinBar API retains its own minute/timeframe handling and must not be mistaken for a core close-time signal mask.

See [PinBar variants](pinbar_variants.md) for both executable forms and their differences.
