"""Regression: equivalent timestamps must not depend on pandas storage units."""
import pandas as pd
import pytest
from atar.synthetic import market
from atar.temporal import data_digest, rolling_folds, validate_ohlc


@pytest.mark.parametrize("unit", ["s", "ms", "us", "ns"])
def test_fold_and_data_identity_independent_of_timestamp_resolution(unit):
    reference = market(bars=500)
    reference.index = reference.index.as_unit("ns")
    converted = reference.copy()
    converted.index = converted.index.as_unit(unit)
    assert converted.index.unit == unit
    validate_ohlc(converted)
    assert data_digest(converted) == data_digest(reference)
    kwargs = dict(warmup=10, train=100, validation=50, final=50, step=50)
    expected = rolling_folds(reference.index, **kwargs)
    actual = rolling_folds(converted.index, **kwargs)
    assert actual == expected
    assert all(a.final.end <= b.final.start for a, b in zip(actual, actual[1:]))
    with pytest.raises(ValueError, match="Regular index"):
        rolling_folds(converted.index.delete(25), **kwargs)
