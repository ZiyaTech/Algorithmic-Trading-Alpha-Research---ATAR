"""A reproducible eager-versus-progressive research experiment on artificial data."""
from __future__ import annotations
from dataclasses import asdict
import html
import json
import platform
from pathlib import Path
import time
import numpy as np
import pandas as pd
from atar import __version__
from atar.identity import digest
from atar.temporal import validate_ohlc, data_digest, rolling_folds
from atar.synthetic import market
from atar.strategies import generate
from atar.pipeline import Candidate, evaluate_candidates, evaluate_final
from atar.screening import Gate
from atar.backends.reference import Execution, simulate
from atar.artifacts import ResultCache, writer_lock, atomic_json, atomic_text, package_fingerprint

DEFAULT_CONFIG = {
    "seed": 2026, "bars": 3200,
    "windows": {"warmup": 200, "train": 1000, "validation": 700, "final": 700, "step": 700},
    "train_gate": {"min_trades": 3, "min_return": -0.02, "min_profit_factor": None},
    "validation_gate": {"min_trades": 2, "min_return": None, "min_profit_factor": 0.8},
}


def demo_candidates() -> list[Candidate]:
    # Public-native illustrative settings, not an exported optimization grid.
    specifications = {
        "pinbar_emarsi": [{"pinbar_ratio": x, "fast_ema_period": 10, "slow_ema_period": 30, "rsi_period": 7} for x in (0.55, 0.7)],
        "pinbar_emarsi_ih": [{"pinbar_ratio": x, "fast_ema_period": 10, "slow_ema_period": 30, "rsi_period": 7} for x in (0.55, 0.7)],
        "rainbow_ema": [{"lookback_bars": x, "pullback_level": 7} for x in (3, 7)],
        "bill_williams": [{"threshold": x, "ao_cross_window": 16} for x in (0.0005, 0.002)],
        "trend_score": [{"ema_periods_choice": x, "bar_size_threshold": 0.0005, "price_threshold": 0.0005} for x in (1, 3)],
        "r3": [{"rsi_period": 2, "rsi_streak_bars": x, "ema_period": 90} for x in (2, 3)],
    }
    candidates = []
    for strategy, settings in specifications.items():
        for parameters in settings:
            for holding in (12, 30):
                execution = asdict(Execution(max_holding_bars=holding))
                candidates.append(Candidate.make(strategy, parameters, execution))
    return sorted(candidates, key=lambda c: c.id)


class ReferenceEvaluator:
    def __init__(self, bars, cache_root: Path, *, namespace: str):
        self.bars = validate_ohlc(bars)
        self.cache = ResultCache(cache_root / namespace)
        self.context = {"schema": 1, "data_sha256": data_digest(bars),
                        "public_code_sha256": package_fingerprint(), "backend": "ohlc-reference-v1",
                        "numpy": np.__version__, "pandas": pd.__version__, "python": platform.python_version()}
        self.hits = self.simulations = 0

    def __call__(self, candidate, window):
        context = {**self.context, "candidate_id": candidate.id, "strategy": candidate.strategy,
                   "parameters": candidate.parameters, "execution": candidate.execution,
                   "window": window.as_dict()}
        def compute():
            # The signal function cannot see even one bar at/after this stage end.
            prefix = self.bars.loc[self.bars.index < window.end]
            signals = generate(candidate.strategy, prefix, candidate.parameters)
            result = simulate(prefix, signals, window, Execution(**candidate.execution))
            return {"candidate_id": candidate.id, "window": window.as_dict(), **result}
        result, cached = self.cache.get_or_compute(context, compute)
        if result.get("candidate_id") != candidate.id or result.get("window") != window.as_dict():
            raise RuntimeError("Result identity/window mismatch")
        metrics = result["metrics"]
        count = metrics["trades_count"]
        if type(count) is not int or count < 0 or count != len(result["trades"]):
            raise RuntimeError("Invalid result trade count")
        if not np.isfinite(metrics["fixed_notional_return"]):
            raise RuntimeError("Invalid return")
        self.hits += int(cached)
        self.simulations += int(not cached)
        return metrics


def _table(frame):
    return frame.to_html(index=False, escape=True, border=0) if len(frame) else "<p>No rows. This is a valid experiment outcome.</p>"


def render_report(summary: dict, counts: pd.DataFrame, final: pd.DataFrame, comparison: dict) -> str:
    cards = [("Candidates", summary["candidate_count"]), ("Rolling folds", summary["fold_count"]),
             ("Avoided selection evaluations", summary["avoided_evaluations"]),
             ("Shortlists identical", str(summary["identical_shortlists"]).lower())]
    card_html = "".join(f"<div class='card'><span>{html.escape(k)}</span><strong>{html.escape(str(v))}</strong></div>" for k,v in cards)
    return """<!doctype html><html lang='en'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'><title>ATAR · Research demonstration</title>
<style>
:root{color-scheme:light}body{margin:0;background:#f5f7fa;color:#182535;font:16px/1.65 system-ui,sans-serif}
main{max-width:1080px;margin:auto;padding:48px 28px}header{border-top:5px solid #276777;padding-top:28px}
.eyebrow{letter-spacing:.2em;font-size:12px;font-weight:700;color:#276777}h1{font-size:44px;line-height:1.15;max-width:850px}
h2{margin-top:44px;font-size:25px}.lead{font-size:19px;max-width:850px;color:#526373}
.cards{display:flex;flex-wrap:wrap;gap:16px;margin:32px 0}.card{flex:1;min-width:160px;background:white;padding:22px;border:1px solid #dae2e8;border-radius:10px}
.card span{display:block;font-size:13px;color:#526373}.card strong{font-size:30px;font-weight:650}
.table{overflow:auto}table{width:100%;background:white;border-collapse:collapse;font-size:13px}th,td{padding:10px 13px;text-align:left;border-bottom:1px solid #dae2e8}th{background:#e9eff4}
.note{border-left:4px solid #276777;padding:16px 22px;background:#edf3f6}code{font-size:13px;overflow-wrap:anywhere}
footer{margin-top:50px;padding-top:20px;border-top:1px solid #cad5df;font-size:13px;color:#526373}
</style></head><body><main><header><div class='eyebrow'>ATAR / EXECUTABLE RESEARCH NOTE</div>
<h1>Same research decision.<br>Less unnecessary computation.</h1>
<p class='lead'>A controlled comparison of eager and progressive evaluation, using artificial OHLC data and independently evaluated strategy candidates.</p></header>
""" + card_html.join(["<section class='cards'>", "</section>"]) + """
<div class='note'>This demonstrates software behavior, not predictive alpha. Selection-validation is used to filter candidates. A separate final interval is evaluated only after the shortlist is frozen.</div>
<h2>Measured work</h2><p>Counts measure backend requests, not a universal runtime speedup. Eager and progressive modes use separate caches. Repeated runs expose cache hits. Runtime varies by environment and execution order.</p>
<div class='table'>""" + _table(counts) + """</div>
<h2>Final evaluation · reporting only</h2><p>Returns are additive fixed-notional research returns. They are not leveraged portfolio returns or live performance. Empty and negative results are retained.</p>
<div class='table'>""" + _table(final) + """</div>
<h2>PinBar variants · active-event comparison</h2><p>This run compares completed-bar reference vectorized and IH-derived state-machine signals on this synthetic data, not the original licensed minute-aligned VBT implementation.</p><pre>""" + html.escape(json.dumps(comparison, indent=2)) + """</pre>
<p>The author has observed approximately 80% signal overlap in prior research. That is a context-dependent author observation, not a benchmark reproduced or guaranteed by this release. Non-signal bars are excluded from the overlap denominator here.</p>
<h2>Reproducibility</h2><p>Configuration, public code and synthetic data fingerprints are recorded in <code>run.json</code>. Per-candidate decisions and rejection reasons are in <code>candidate_audit.csv</code>.</p>
<footer>Algorithmic Trading Alpha Research · Yingrui Shang / ZiyaTech · Research software, not trading recommendations.</footer>
</main></body></html>"""


def compare_pinbar(bars) -> dict:
    parameters = {"pinbar_ratio": 0.65, "fast_ema_period": 10, "slow_ema_period": 30, "rsi_period": 7}
    a, b = (generate(s, bars, parameters) for s in ("pinbar_emarsi", "pinbar_emarsi_ih"))
    def events(signal):
        return {(t.isoformat(), side) for side, mask in (("long", signal.long), ("short", signal.short)) for t in mask.index[mask]}
    x, y = events(a), events(b)
    common, union = len(x & y), len(x | y)
    return {"comparison": "synthetic_completed_bar_reference_vs_ih_signal_core",
            "vectorized_events": len(x), "serialized_events": len(y), "matched_events": common,
            "active_event_jaccard": common / union if union else None,
            "vectorized_recall": common / len(x) if x else None,
            "serialized_recall": common / len(y) if y else None}


def run_demo(output: Path, config: dict | None = None) -> dict:
    config = json.loads(json.dumps(DEFAULT_CONFIG if config is None else config))
    if set(config) != set(DEFAULT_CONFIG):
        raise ValueError("Demo configuration fields must match the documented schema")
    bars = market(bars=config["bars"], seed=config["seed"])
    folds = rolling_folds(bars.index, **config["windows"])
    train_gate, validation_gate = Gate(**config["train_gate"]), Gate(**config["validation_gate"])
    candidates = demo_candidates()
    output = Path(output)
    # Do not overwrite arbitrary existing files or follow any output symlink.
    if output.exists() and any(p.is_symlink() for p in output.rglob("*")):
        raise ValueError("Output tree contains a symlink")
    identity = {"config": config, "public_code_sha256": package_fingerprint(),
                "data_sha256": data_digest(bars), "candidate_ids": [c.id for c in candidates],
                "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__}
    signature = digest(identity)
    with writer_lock(output):
        manifest = output / "run.json"
        if manifest.exists():
            prior = json.loads(manifest.read_text())
            if prior.get("signature") != signature:
                raise ValueError("Output belongs to a different experiment. Use a fresh directory")
        elif any(p.name != ".writer.lock" for p in output.iterdir()):
            raise ValueError("Refusing to write into a nonempty, unrecognized output directory")
        atomic_json(manifest, {"status": "RUNNING", "signature": signature, **identity})
        (output / "COMPLETE.json").unlink(missing_ok=True)
        counts, audits, finals, shortlists = [], [], [], []
        for number, fold in enumerate(folds):
            runs = []
            for mode in ("eager", "progressive"):
                evaluator = ReferenceEvaluator(bars, output / "cache", namespace=mode)
                run = evaluate_candidates(candidates, fold, train_gate, validation_gate, evaluator, mode=mode)
                counts.append({"fold": number, "mode": mode, "requested_evaluations": run.calls,
                               "actual_simulations": evaluator.simulations, "cache_hits": evaluator.hits,
                               "seconds": round(run.seconds, 6), "shortlist_count": len(run.shortlist)})
                audits.extend({"fold": number, "mode": mode, **row} for row in run.audit)
                runs.append(run)
            if [c.id for c in runs[0].shortlist] != [c.id for c in runs[1].shortlist]:
                raise RuntimeError("Eager/progressive shortlist mismatch")
            selected = runs[1].shortlist
            shortlists.extend({"fold": number, "candidate_id": c.id, "strategy": c.strategy,
                               "parameters": c.parameters_json, "execution": c.execution_json} for c in selected)
            # Freeze the decision before any final-period metrics are computed.
            atomic_text(output / "shortlist.csv", pd.DataFrame(shortlists, columns=[
                "fold", "candidate_id", "strategy", "parameters", "execution"]).to_csv(index=False))
            final_evaluator = ReferenceEvaluator(bars, output / "cache", namespace="final")
            finals.extend({"fold": number, **row} for row in evaluate_final(selected, fold, final_evaluator))
        counts_df = pd.DataFrame(counts)
        final_df = pd.DataFrame(finals, columns=["fold", "candidate_id", "strategy", "trades_count",
            "fixed_notional_return", "mean_trade_return", "win_rate", "profit_factor", "max_drawdown_fixed_notional"])
        comparison = compare_pinbar(bars)
        requested = counts_df.groupby("mode").requested_evaluations.sum()
        summary = {"version": __version__, "candidate_count": len(candidates), "fold_count": len(folds),
                   "identical_shortlists": True,
                   "avoided_evaluations": int(requested["eager"] - requested["progressive"]),
                   "selection_counts": counts, "final_rows": len(finals)}
        for name, frame in (("candidate_audit.csv", pd.DataFrame(audits)), ("evaluation_counts.csv", counts_df),
                            ("final_evaluation.csv", final_df)):
            atomic_text(output / name, frame.to_csv(index=False))
        atomic_json(output / "pinbar_comparison.json", comparison)
        atomic_json(output / "summary.json", summary)
        atomic_text(output / "report.html", render_report(summary, counts_df, final_df, comparison))
        atomic_json(manifest, {"status": "COMPLETE", "signature": signature, **identity,
                              "windows": [{"fold": i, "train": f.train.as_dict(), "validation": f.validation.as_dict(),
                                           "final": f.final.as_dict()} for i, f in enumerate(folds)]})
        atomic_json(output / "COMPLETE.json", {"signature": signature, "summary_sha256": digest(summary)})
        return summary
