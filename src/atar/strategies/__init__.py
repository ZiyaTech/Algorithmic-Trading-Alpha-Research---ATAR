"""Five families and a second, explicitly distinct PinBar implementation."""
from . import pinbar_emarsi, pinbar_emarsi_ih, rainbow_ema, bill_williams, trend_score, r3

REGISTRY = {
    "pinbar_emarsi": pinbar_emarsi.generate,
    "pinbar_emarsi_ih": pinbar_emarsi_ih.generate,
    "rainbow_ema": rainbow_ema.generate,
    "bill_williams": bill_williams.generate,
    "trend_score": trend_score.generate,
    "r3": r3.generate,
}


def generate(name, bars, parameters=None, *, provider=None):
    if name not in REGISTRY:
        raise ValueError(f"Unknown strategy {name!r}. Choose from {sorted(REGISTRY)}")
    return REGISTRY[name](bars, provider=provider, **(parameters or {}))
