# Same research decision, less unnecessary computation

## Problem

Later evaluations are wasted when a candidate has already failed a required earlier criterion. The question here is about computation, not whether the criteria predict profit.

For `N` independent candidates, eager evaluation computes train and validation metrics for all `N`, then applies both gates. Progressive evaluation computes train for all `N` and validation only for the `S` train survivors. With deterministic independent evaluations and identical gates, both procedures select the same set. They require `2N` and `N + S` evaluations respectively.

The demonstration asserts shortlist identity. It reports actual backend requests, simulations, cache hits and wall time. Fewer evaluations do not guarantee proportional runtime savings. Different stages can have different costs, and caching, signal reuse and machine load affect elapsed time.

## Example and audit

Run `python -m atar demo --output artifacts/demo`. Inspect `candidate_audit.csv` to see which train failures were not evaluated later. The example has no random metric generator. Its trades and returns are computed from artificial OHLC by the documented reference simulator.

A mock evaluator remains useful in unit tests to isolate routing. Those tests are labelled by their purpose; their fabricated numbers are not used as the public demonstration.

## Final evaluation is not another tuning stage

Selection-validation is part of model selection. Once the shortlist is frozen, a later interval is evaluated for reporting only. The final results cannot add, remove or rank shortlisted candidates. Empty selections remain empty. The demo does not loosen gates automatically to generate an attractive outcome.

In rolling research, final intervals are non-overlapping in the provided fold generator. Earlier final data may become available history for a later chronological fold, which is normal walk-forward behavior. This does not justify retroactively changing the experiment after seeing results.

## Conditions under which the equivalence can fail

The simple proof does not cover shared capital, cross-candidate netting, execution priority, state carried between candidates, stochastic evaluators without controlled randomness, or gates that change based on the candidates already evaluated. Those require additional design and tests. The example intentionally models independent candidates.

Repeated human experimentation can still create selection bias. A clean temporal split in one run is not a statistical guarantee across many researcher decisions.
