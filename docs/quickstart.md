# Quickstart

## Install and run

Use Python 3.11+. Create a virtual environment and install the repository with `python -m pip install -e ".[dev]"`. Run:

```bash
python -m atar demo --config examples/staged_research/demo.json --output artifacts/demo
python -m pytest -q
```

Open `artifacts/demo/report.html` directly in your browser. No web server, login, data download or commercial dependency is needed for this example. Dependencies must be installed first.

The output path must be new or belong to exactly the same experiment. An unrecognized nonempty directory is rejected. Re-running the same command verifies and reuses cached results. Changing configuration, public code, dependency versions or synthetic data requires a fresh output directory. Do not delete a writer lock while another process is using it.

## Inspect the outputs

| File | Purpose |
|---|---|
| `run.json` | Effective config, windows, software versions, data and public-code fingerprints |
| `candidate_audit.csv` | Train/validation outcomes, rejected candidates and reasons |
| `evaluation_counts.csv` | Requests, actual simulations, cache hits and measured seconds |
| `shortlist.csv` | Frozen illustrative selection, written before final evaluation |
| `final_evaluation.csv` | Reporting-only later-period metrics; not a selection input |
| `pinbar_comparison.json` | Synthetic active-event overlap, with explicit denominators |
| `report.html` | Readable overview with the above distinctions |
| `COMPLETE.json` | Successful completion and summary identity |

If an interrupted run leaves old human-readable outputs, treat them as invalid unless `run.json` is COMPLETE and `COMPLETE.json` matches its signature. The cache is not a substitute for this completion contract.

## Compare PinBar implementations

```bash
python -m atar compare-pinbar --seed 2026 --bars 3200
```

This compares the completed-bar reference vectorized implementation with its IH-derived signal-core variant. It does not measure the original minute-aligned VBT path. See [the variants guide](pinbar_variants.md) before interpreting the numbers.

## Use VBT Pro

Use your independently installed, licensed VBT Pro environment. Nothing is bundled, downloaded or activated by ATAR. The optional `VBTProIndicators` adapter can be passed to any completed-bar strategy. The preserved minute-aligned PinBar API is a separate integration because its returned mask timestamps have different execution semantics.

```python
from atar.indicators import VBTProIndicators
from atar.strategies import generate
from atar.synthetic import market

signals = generate("r3", market(), {"rsi_period": 2, "rsi_streak_bars": 3, "ema_period": 90},
                   provider=VBTProIndicators())
```

Optional licensed-runtime tests are skipped when that dependency is absent. A skipped test is not a compatibility pass.
