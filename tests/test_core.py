import json
from dataclasses import asdict
import numpy as np
import pandas as pd
import pytest
from atar.identity import candidate_id, canonical_json
from atar.temporal import Window, Fold, validate_ohlc, complete_bars, rolling_folds
from atar.sampling import lhs_targets, sample_existing
from atar.screening import Gate
from atar.config import load_config, deep_merge
from atar.artifacts import ResultCache, writer_lock
from atar.synthetic import market
from atar.indicators import ReferenceIndicators
from atar.pipeline import Candidate, evaluate_candidates, evaluate_final


def test_candidate_order_and_numeric_normalization():
    assert candidate_id("x", {"a": 2, "b": 3.2}) == candidate_id("x", {"b": 3.2, "a": 2.0})
    assert candidate_id("x", {"a": 2}) != candidate_id("y", {"a": 2})
    assert candidate_id("x", {"a": 2}) != candidate_id("x", {"a": 2}, implementation="other")
    assert candidate_id("x", {"a": 2}) != candidate_id("x", {"a": 2}, timeframe="2h")


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf, object()])
def test_bad_identity_values(value):
    with pytest.raises((ValueError, TypeError)):
        candidate_id("x", {"v": value})


def test_mapping_cannot_override_identity():
    assert candidate_id("x", {"strategy": "y"}) != candidate_id("y", {})
    with pytest.raises(TypeError):
        canonical_json({1: "x"})


def test_temporal_windows():
    with pytest.raises(ValueError):
        Window("x", "2021-01-01", "2021-01-02")
    a = Window("train", "2021-01-01T00:00Z", "2021-01-02T00:00Z")
    with pytest.raises(ValueError):
        Fold(a, Window("validation", "2021-01-01T12:00Z", "2021-01-03T00:00Z"),
             Window("final", "2021-01-03T00:00Z", "2021-01-04T00:00Z"))


@pytest.mark.parametrize("fault", ["duplicate", "reverse", "gap", "naive", "price", "bounds"])
def test_ohlc_rejects_bad_data(fault):
    d = market(bars=20)
    if fault == "duplicate": d.index = pd.DatetimeIndex([d.index[0], *d.index[:-1]])
    if fault == "reverse": d = d.iloc[::-1]
    if fault == "gap": d = d.drop(d.index[3])
    if fault == "naive": d.index = d.index.tz_localize(None)
    if fault == "price": d.iloc[1, 0] = np.nan
    if fault == "bounds": d.iloc[1, 1] = 1
    with pytest.raises(ValueError): validate_ohlc(d)


def test_resampling_drops_incomplete_bar():
    d = market(bars=7)
    out = complete_bars(d, "3h")
    assert len(out) == 2
    assert out.iloc[0].close == d.iloc[2].close
    assert out.iloc[0].open == d.iloc[0].open
    with pytest.raises(ValueError): complete_bars(d, "90min")


def test_nonoverlapping_rolling_final_windows():
    f = rolling_folds(market(bars=500).index, warmup=10, train=100, validation=50, final=50, step=50)
    assert len(f) > 1
    assert all(a.final.end <= b.final.start for a,b in zip(f, f[1:]))
    with pytest.raises(ValueError):
        rolling_folds(market(bars=500).index, warmup=10, train=100, validation=50, final=50, step=20)


def test_lhs_stratification():
    a = lhs_targets(11, 3, seed=5)
    assert np.array_equal(a, lhs_targets(11, 3, seed=5))
    for j in range(3): assert sorted((a[:, j] * 11).astype(int)) == list(range(11))


@pytest.mark.parametrize("budget", [0, 1, 5, 10, 20])
def test_sampling_only_existing_rows_with_stable_order(budget):
    df = pd.DataFrame({"candidate_id": [f"c{i:02}" for i in range(10)], "a": np.arange(10), "b": 1.0})
    a = sample_existing(df, ["a", "b"], budget, seed=3)
    b = sample_existing(df.sample(frac=1, random_state=7), ["a", "b"], budget, seed=3)
    pd.testing.assert_frame_equal(a, b)
    assert len(a) == min(budget, 10)
    assert set(a.candidate_id) <= set(df.candidate_id)


def test_sampling_invalid_and_duplicate():
    d = pd.DataFrame({"candidate_id": ["x", "x"], "a": [1.0, 2.0]})
    with pytest.raises(ValueError): sample_existing(d, ["a"], 1, seed=1)
    d.candidate_id = ["x", "y"]; d.loc[0, "a"] = np.inf
    with pytest.raises(ValueError): sample_existing(d, ["a"], 1, seed=1)


@pytest.mark.parametrize("bad", ["3", True, -1, 0.5])
def test_gate_invalid_count_config(bad):
    with pytest.raises(ValueError): Gate(min_trades=bad)


def test_gate_undefined_and_infinite_pf():
    gate = Gate(min_trades=1, min_profit_factor=1.0)
    assert gate.decide({"trades_count": 4, "profit_factor": "+inf"})[0]
    assert not gate.decide({"trades_count": 4, "profit_factor": None})[0]
    assert not gate.decide({"trades_count": 4, "profit_factor": "-inf"})[0]
    assert not gate.decide({"trades_count": -1, "profit_factor": 2.0})[0]
    with pytest.raises(ValueError): gate.decide({"trades_count": 4})


def test_config_includes_and_no_mutation(tmp_path):
    (tmp_path / "base.jsonc").write_text('{"a":{"x":1,"y":2},"b":[1,2]}')
    (tmp_path / "child.jsonc").write_text('{"include":"base.jsonc","a":{"x":3},"b":[9]}')
    assert load_config(tmp_path / "child.jsonc") == {"a": {"x":3,"y":2}, "b":[9]}
    original={"a":{"x":1}}; merged=deep_merge(original, {"b":2});merged["a"]["x"]=5
    assert original["a"]["x"] == 1
    (tmp_path / "base.jsonc").write_text('{"include":"child.jsonc"}')
    with pytest.raises(ValueError): load_config(tmp_path / "base.jsonc")


def test_duplicate_json_keys_fail(tmp_path):
    p=tmp_path/'x.jsonc';p.write_text('{"x":1,"x":2}')
    with pytest.raises(ValueError): load_config(p)


def test_cache_reuse_invalidation_and_corruption(tmp_path):
    cache=ResultCache(tmp_path)
    count=[]
    def compute(): count.append(1);return {"x":2}
    assert cache.get_or_compute({"data":"a"}, compute) == ({"x":2},False)
    assert cache.get_or_compute({"data":"a"}, compute) == ({"x":2},True)
    assert cache.get_or_compute({"data":"b"}, compute) == ({"x":2},False)
    assert len(count)==2
    p=next(tmp_path.glob('*.json'));p.write_text('broken')
    with pytest.raises(RuntimeError):
        for c in ({"data":"a"},{"data":"b"}): cache.get_or_compute(c, compute)


def test_lock_is_exclusive(tmp_path):
    with writer_lock(tmp_path):
        with pytest.raises(RuntimeError):
            with writer_lock(tmp_path): pass
    assert not (tmp_path/'.writer.lock').exists()


def test_eager_progressive_equivalence_and_final_separation():
    fold=rolling_folds(market(bars=100).index,warmup=10,train=30,validation=20,final=20,step=20)[0]
    candidates=[Candidate.make("x",{"n":n},{}) for n in range(6)]
    calls=[]
    def evaluate(c,w):
        calls.append(w.name)
        n=c.parameters['n']
        return {'trades_count': n, 'fixed_notional_return': n/100}
    eager=evaluate_candidates(candidates,fold,Gate(3),Gate(4),evaluate,mode='eager')
    progressive=evaluate_candidates(candidates,fold,Gate(3),Gate(4),evaluate)
    assert [c.id for c in eager.shortlist] == [c.id for c in progressive.shortlist]
    assert eager.calls==12 and progressive.calls==9
    assert 'final' not in calls
    assert len(evaluate_final(progressive.shortlist,fold,evaluate))==2
    assert calls[-2:]==['final','final']


def test_zero_survivors_do_not_run_validation():
    fold=rolling_folds(market(bars=100).index,warmup=10,train=30,validation=20,final=20,step=20)[0]
    calls=[]
    def evaluate(c,w): calls.append(w.name);return {'trades_count':0}
    result=evaluate_candidates([Candidate.make('x',{}, {})],fold,Gate(1),Gate(1),evaluate)
    assert calls==['train'] and result.shortlist==[]


def test_reference_indicators_hand_calculated():
    i=ReferenceIndicators();s=pd.Series([1.,2.,3.,4.,5.])
    assert i.ema(s,3).iloc[2:].tolist()==[2.,3.,4.]
    assert i.rsi(s,2).iloc[2:].tolist()==[100.,100.,100.]
    assert i.rsi(pd.Series([1.,1.,1.]),2).iloc[-1]==0.
