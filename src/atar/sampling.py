"""Deterministic space coverage without ranking by backtest performance."""
from __future__ import annotations
import numpy as np
import pandas as pd


def lhs_targets(n: int, dimensions: int, *, seed: int) -> np.ndarray:
    if type(n) is not int or n < 0 or type(dimensions) is not int or dimensions < 1:
        raise ValueError("Invalid LHS shape")
    if n == 0:
        return np.empty((0, dimensions))
    rng = np.random.default_rng(seed)
    out = (np.arange(n)[:, None] + rng.random((n, dimensions))) / n
    for j in range(dimensions):
        rng.shuffle(out[:, j])
    return out


def sample_existing(frame: pd.DataFrame, columns: list[str], budget: int, *, seed: int) -> pd.DataFrame:
    """Nearest-unused rows to LHS targets. Stable ties follow candidate_id order.

    This preserves actual supplied rows; it does not fabricate parameter values.
    It is a coverage heuristic, not a guaranteed optimal design or alpha selector.
    """
    if type(budget) is not int or budget < 0 or not columns or len(set(columns)) != len(columns):
        raise ValueError("Invalid budget or feature columns")
    if "candidate_id" not in frame or frame.candidate_id.isna().any() or frame.candidate_id.duplicated().any():
        raise ValueError("Unique non-null candidate_id required")
    if not frame.candidate_id.map(lambda x: isinstance(x, str) and bool(x.strip())).all():
        raise ValueError("candidate_id must contain nonblank strings")
    x = frame[columns].to_numpy(dtype=float)
    if not np.isfinite(x).all():
        raise ValueError("Sampling features must be finite")
    work = frame.sort_values("candidate_id", kind="stable").reset_index(drop=True)
    if len(work) <= budget or budget == 0:
        return work.iloc[:budget].copy()
    x = work[columns].to_numpy(dtype=float)
    low, high = x.min(axis=0), x.max(axis=0)
    span = np.where(high == low, 1, high - low)
    x = (x - low) / span
    available = np.ones(len(work), dtype=bool)
    chosen = []
    for target in lhs_targets(budget, len(columns), seed=seed):
        options = np.flatnonzero(available)
        j = options[np.argmin(((x[options] - target) ** 2).sum(axis=1))]
        chosen.append(int(j))
        available[j] = False
    return work.iloc[sorted(chosen)].reset_index(drop=True)
