"""Independent-candidate eager/progressive evaluation, with auditable decisions."""
from __future__ import annotations
from dataclasses import dataclass
import json
import time
from atar.identity import candidate_id, canonical_json
from atar.temporal import Fold
from atar.screening import Gate


@dataclass(frozen=True)
class Candidate:
    strategy: str
    parameters_json: str
    execution_json: str
    id: str

    @classmethod
    def make(cls, strategy: str, parameters: dict, execution: dict, *, timeframe="1h"):
        params = {"signal": parameters, "execution": execution}
        identity = candidate_id(strategy, params, timeframe=timeframe)
        return cls(strategy, canonical_json(parameters), canonical_json(execution), identity)

    @property
    def parameters(self):
        return json.loads(self.parameters_json)

    @property
    def execution(self):
        return json.loads(self.execution_json)


@dataclass
class EvaluationRun:
    mode: str
    shortlist: list[Candidate]
    audit: list[dict]
    calls: int
    seconds: float


def evaluate_candidates(candidates: list[Candidate], fold: Fold, train_gate: Gate,
                        validation_gate: Gate, evaluate, *, mode="progressive") -> EvaluationRun:
    """Selection never receives final-period metrics. evaluate returns a metrics dict."""
    if mode not in ("eager", "progressive"):
        raise ValueError("mode must be eager or progressive")
    if len({c.id for c in candidates}) != len(candidates):
        raise ValueError("Duplicate candidate identities")
    audit, shortlist = [], []
    calls = 0
    start = time.perf_counter()
    for c in candidates:
        first = evaluate(c, fold.train)
        calls += 1
        ok, why = train_gate.decide(first)
        audit.append({"candidate_id": c.id, "strategy": c.strategy, "stage": "train",
                      "status": "pass" if ok else "reject", "reasons": "|".join(why), **first})
        if mode == "progressive" and not ok:
            audit.append({"candidate_id": c.id, "strategy": c.strategy, "stage": "validation",
                          "status": "not_evaluated", "reasons": "rejected_in_train"})
            continue
        second = evaluate(c, fold.validation)
        calls += 1
        ok_second, why_second = validation_gate.decide(second)
        audit.append({"candidate_id": c.id, "strategy": c.strategy, "stage": "validation",
                      "status": "pass" if ok_second else "reject", "reasons": "|".join(why_second), **second})
        if ok and ok_second:
            shortlist.append(c)
    return EvaluationRun(mode, shortlist, audit, calls, time.perf_counter() - start)


def evaluate_final(shortlist: list[Candidate], fold: Fold, evaluate) -> list[dict]:
    """Reporting only: never adds, removes, ranks or changes shortlisted candidates."""
    return [{"candidate_id": c.id, "strategy": c.strategy, **evaluate(c, fold.final)} for c in shortlist]
