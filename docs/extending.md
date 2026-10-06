# Extend one boundary at a time

## Bring a strategy

Write a function accepting validated completed OHLC bars and parameters, and return `Signals(long, short)` on exactly the same index. Do not place orders or embed data credentials. Add it to `REGISTRY` only after testing prefix invariance, output alignment and parameter validation.

```python
from atar.strategies.common import signals


def my_signal(bars):
    up = bars.close > bars.close.shift(3)
    down = bars.close < bars.close.shift(3)
    return signals(up, down, bars.index)
```

That example teaches the interface, not a profitable strategy. For a more substantive source example, inspect `rainbow_ema.py` or the sequential PinBar state machine.

## Bring an evaluator

`evaluate_candidates` accepts a callback `evaluate(candidate, window)` returning a metric dictionary. Every active gate metric must be present. Restrict data delivered to signal generation to information available before the evaluation end. Keep candidates independent to retain the eager/progressive equivalence.

Version the backend and include its data, code and configuration identity in any cache key. Do not reuse reference-backend results for a different execution model. Supply no final-period metrics to selection.

## Bring data

Normalize bars to explicit UTC, label by bar open, and validate OHLC bounds. The reference simulator requires regular bars and rejects missing timestamps. A real-market adapter must own trading sessions, holidays, splits/rolls, timezone conversion and missing data policy. Merely renaming a synthetic instrument is not validated support for another asset class.

## Use a batch scheduler

The optional Slurm script runs three independent seeds with bounded library threads. Run it from the repository root in an activated environment and adapt resource requests to your cluster. It does not provision infrastructure, configure credentials or claim a measured multi-node scaling result.

```bash
bash -n examples/slurm/demo_array.sh
sbatch examples/slurm/demo_array.sh
```

Submission is always an explicit user action. No Python import submits jobs.
