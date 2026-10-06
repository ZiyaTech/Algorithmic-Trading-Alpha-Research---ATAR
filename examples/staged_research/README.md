# Staged research example

From the repository root:

```bash
python -m atar demo --config examples/staged_research/demo.json --output artifacts/demo
```

This deliberately modest candidate population isolates the difference between eager and progressive routing. Every candidate is evaluated independently. No production optimizer or selected parameter inventory is used.

The separate sampling example demonstrates coverage-based down-selection. It is not silently applied to one side of the eager/progressive comparison.

The `sample/` directory records counters from a measured local cold run of this public code on artificial input. Runtime is environment-specific. Run the example to create the complete HTML report, audit, manifest, final-period results and trade-cache artifacts. Do not confuse synthetic shortlisted candidates with a live deployment.
