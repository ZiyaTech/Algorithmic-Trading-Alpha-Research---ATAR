"""Explicit JSONC inheritance with cycle detection and immutable deep merges."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json5


def deep_merge(parent: dict, child: dict) -> dict:
    if not isinstance(parent, dict) or not isinstance(child, dict):
        raise TypeError("Configuration roots must be objects")
    out = deepcopy(parent)
    for k, v in child.items():
        out[k] = deep_merge(out[k], v) if isinstance(out.get(k), dict) and isinstance(v, dict) else deepcopy(v)
    return out


def load_config(path: str | Path, _stack: tuple[Path, ...] = ()) -> dict:
    path = Path(path).expanduser().resolve()
    if path in _stack:
        raise ValueError("Circular configuration include")
    with path.open(encoding="utf-8") as stream:
        raw = json5.load(stream, allow_duplicate_keys=False)
    if not isinstance(raw, dict):
        raise ValueError("Configuration root must be an object")
    keys = [k for k in ("include", "extends") if k in raw]
    if len(keys) > 1:
        raise ValueError("Use one include key only")
    if not keys:
        return raw
    parent = raw.pop(keys[0])
    if not isinstance(parent, str) or not parent:
        raise ValueError("Include must be a nonempty path string")
    return deep_merge(load_config(path.parent / parent, (*_stack, path)), raw)
