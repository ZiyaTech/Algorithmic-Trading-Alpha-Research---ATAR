# PinBarEMARSI: vectorized and IH serialized implementations

Both implementation styles are included deliberately. Their differences are known characteristics, not a reason to omit one or force agreement.

The author reports that signals overlapped approximately **80% of the time in prior research**. This is an author-reported, context-dependent observation. The prior dataset, time tolerance and exact denominator are not shipped with this release, so that number is not represented as a reproduced benchmark or a universal property. It does not imply identical trade counts, fills or returns.

## Four clearly identified entry points

| Entry point | What it is | Timestamp convention |
|---|---|---|
| `atar.strategies.pinbar_emarsi.generate` | Standalone completed-bar adaptation of the vectorized formula | Decision belongs to the completed bar; fill next bar |
| `atar.strategies.pinbar_emarsi_ih.generate` / `PinBarEMARSISerialized` | Sequential IH-derived signal state transitions | Same completed-bar convention for controlled comparisons |
| `atar.integrations.vbtpro_pinbar.pinbaremarsi_signal` | Cleaned original VBT Pro minute/timeframe API | Minute-indexed executable-time mask; do not shift again blindly |
| `atar.integrations.ih_pinbar.PinBarEMARSIStrategy` | Standalone IH quote-callback adaptation | New quote-bar event examines the previous completed bar and returns an order intent |

## Logic retained rather than homogenized

The vectorized tail comparison uses `>=`; the IH helper compares a ratio with strict `>`. The vectorized EMA sign state treats equality as the nonpositive side. The IH crossover helper uses strict inequalities on both current and previous EMA values. Both latch RSI extremes and reset state on their respective crossover definitions.

The quote callback retains first-tick initialization, duplicate/new-bar gating, end-exclusive trading hours, previous-bar and predecessor indicator lookup, open-order suppression and the original bid/ask level formulas. A buy intent uses ask for entry/target and bid for its stop reference. A sell intent uses bid for entry/target and ask for its stop reference.

The standalone completed-bar state machine does not reproduce a live process's initial tick, session history or quote arrival schedule. It exists to isolate the sequential signal logic under controlled inputs.

## What cleanup changed

Private base classes, account sizing, broker submission, operational metadata and deployment coupling were removed. The callback returns a typed `OrderIntent`, leaving order handling to the caller. No account is contacted. Signal inversion and production risk policy are not carried over. Error handling is explicit rather than swallowing exceptions.

The original VBT entry point retains its indicator calls and minute-bar alignment. It adds input checks and cleans redundant code. Core reference indicators and core one-timeframe adapters are separate implementations, not a claimed bit-identical replay of the original live system.

## Reuse the serialized callback

```python
from atar.synthetic import market
from atar.integrations.ih_pinbar import PinBarEMARSIStrategy

bars = market()
strategy = PinBarEMARSIStrategy(
    bars, tail_ratio_threshold=0.65, ema_short_period=10, ema_long_period=30,
    rsi_period=7, stop_loss_ratio=0.012, take_profit_ratio=0.018,
)
for timestamp, bar in bars.iterrows():
    intent = strategy.on_quote_tick(timestamp, bid=bar.open * 0.9999,
                                    ask=bar.open * 1.0001, has_open_order=False)
    if intent is not None:
        print(intent)  # Research intent only. No order is submitted.
```

Here every quote is a synthetic bar-open quote, not a reconstructed tick stream. `has_open_order=False` inspects intents; a real simulator must supply its actual open-position state and execution model. To use the optional indicator dependency, pass `provider=VBTProIndicators()` from `atar.indicators`.

## Measure overlap without counting quiet bars

`python -m atar compare-pinbar` compares the completed-bar reference variants on artificial data. An event is `(timestamp, direction)`. The report includes matched events, active-event intersection-over-union and matched-event recall from each side. If neither side signals, the ratio is undefined (`null`), not 100%.

The reference synthetic run happens to produce identical core signal events. That does not contradict the author's separate historical observation: it does not include the original minute-aligned indicator path, asynchronous quote arrivals or live state. Boundary-specific unit tests deliberately demonstrate differences. No gate is added requiring approximately 80% agreement.
