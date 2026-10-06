"""Run from an installed checkout: python examples/sampling.py."""
import pandas as pd
from atar.identity import candidate_id
from atar.sampling import sample_existing

rows = []
for x in (0.1, 0.3, 0.5, 0.7):
    for y in (1.0, 2.0, 3.0):
        rows.append({"candidate_id": candidate_id("coverage_example", {"x": x, "y": y}), "x": x, "y": y})
frame = pd.DataFrame(rows)
print(sample_existing(frame, ["x", "y"], budget=5, seed=42).to_string(index=False))
