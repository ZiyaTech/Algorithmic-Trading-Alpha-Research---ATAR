# Demonstration results

A local cold run of the public reference example, using artificial data with seed 2026 and the checked-in configuration, produced the following. No seed search or gate relaxation was performed to obtain an attractive result.

| Selection path | Candidate evaluations | Actual simulations | Cache hits | Shortlist |
|---|---:|---:|---:|---:|
| Eager | 48 | 48 | 0 | 11 |
| Progressive | 35 | 35 | 0 | 11 |

The candidate IDs in both shortlists matched exactly. The progressive path avoided 13 of 48 selection evaluations (about 27.1%). This is an evaluation-count result, not a general speedup guarantee. The machine-readable sample records measured runtime for its environment, and repeated local runs will differ.

A separate final interval is evaluated for all 11 shortlisted candidates. Those measurements do not alter the shortlist. Run `python -m atar demo --output artifacts/demo` to create the complete final-period metrics, audit, manifest and HTML report.

For the completed-bar PinBar comparison, the synthetic run produced 72 vectorized and 72 serialized signal events, with 72 matches. The active-event Jaccard ratio was 1.0. This narrowly defined controlled comparison is not a reproduction of the author's historical roughly 80% observation across the original implementation environments. Exact-threshold unit tests demonstrate that the formulas can differ.

The [sample selection summary](../examples/staged_research/sample/summary.json) records observed counters and timings. The [signal comparison](../examples/staged_research/sample/pinbar_comparison.json) records its specific active-event denominator. These are evidence about research software behavior, not an investment strategy.
