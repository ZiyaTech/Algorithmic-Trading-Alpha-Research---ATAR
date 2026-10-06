"""Versioned semantic identities, distinct from experiment and result identities."""
from __future__ import annotations
import hashlib
import json
import math
from collections.abc import Mapping
from numbers import Integral, Real
from typing import Any


def canonical(value: Any) -> Any:
    """Normalize JSON-like values; reject ambiguous and non-finite parameters."""
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Non-finite identity parameter")
        # Integral floats and integers denote the same scalar parameter.
        return int(number) if number.is_integer() else number
    if isinstance(value, Mapping):
        if not all(isinstance(k, str) for k in value):
            raise TypeError("Identity mapping keys must be strings")
        return {k: canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [canonical(v) for v in value]
    raise TypeError(f"Unsupported identity type: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(canonical(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def candidate_id(strategy: str, parameters: Mapping, *, implementation: str = "reference",
                 instrument: str = "SYNTHETIC", timeframe: str = "1h") -> str:
    if not all(isinstance(x, str) and x.strip() == x and x for x in
               (strategy, implementation, instrument, timeframe)):
        raise ValueError("Identity labels must be nonblank strings without surrounding space")
    payload = {"schema": 1, "strategy": strategy, "implementation": implementation,
               "instrument": instrument, "timeframe": timeframe, "parameters": dict(parameters)}
    return "atar_v1_" + digest(payload)
