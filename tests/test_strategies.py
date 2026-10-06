import importlib.util
import numpy as np
import pandas as pd
import pytest
from atar.synthetic import market
from atar.strategies import REGISTRY, generate
from atar.strategies.pinbar_emarsi_ih import check_pinbar, update_rsi_flags, PinBarEMARSISerialized
from atar.integrations.ih_pinbar import PinBarEMARSIStrategy


@pytest.mark.parametrize("name", sorted(REGISTRY))
def test_prefix_invariance_and_boolean_contract(name):
    d=market(bars=350)
    full=generate(name,d)
    prefix=generate(name,d.iloc[:250])
    full.validate(d.index)
    pd.testing.assert_series_equal(full.long.iloc[:250],prefix.long)
    pd.testing.assert_series_equal(full.short.iloc[:250],prefix.short)
    changed=d.copy();changed.iloc[250:]*=2
    altered=generate(name,changed)
    pd.testing.assert_series_equal(full.long.iloc[:250],altered.long.iloc[:250])
    pd.testing.assert_series_equal(full.short.iloc[:250],altered.short.iloc[:250])


def test_ih_strict_tail_boundary():
    assert check_pinbar(11,1,10,9,0.8)==(False,False)
    assert check_pinbar(11,1,10,9,0.79)==(True,False)
    assert check_pinbar(10,10,10,10,0.5)==(False,False)


def test_rsi_cross_resets_and_equality_preserved():
    assert update_rsi_flags(11,10,9,10,90,False,False,80,20)==(False,False)
    assert update_rsi_flags(11,10,10,10,90,False,False,80,20)==(True,False)
    assert update_rsi_flags(11,10,11,10,50,True,False,80,20)==(True,False)


class FixedIndicators:
    def ema(self,s,n):return pd.Series(9.5 if n==2 else 9.,index=s.index)
    def rsi(self,s,n):return pd.Series(90.,index=s.index)


def fixture_bars():
    return pd.DataFrame({'open':9.,'high':11.,'low':1.,'close':10.},
                        index=pd.date_range('2021-01-01',periods=6,freq='h',tz='UTC'))


def test_vectorized_and_ih_intentionally_differ_at_boundary():
    d=fixture_bars();p=dict(pinbar_ratio=.8,fast_ema_period=2,slow_ema_period=3,rsi_period=2)
    a=generate('pinbar_emarsi',d,p,provider=FixedIndicators())
    b=generate('pinbar_emarsi_ih',d,p,provider=FixedIndicators())
    assert a.long.all() and not b.long.any()


def test_serialized_duplicate_and_out_of_order_events():
    d=fixture_bars();m=PinBarEMARSISerialized(pinbar_ratio=.7)
    k=dict(ema_fast=9.5,ema_slow=9.,rsi=90.)
    assert m.on_completed_bar(d.index[1],d.iloc[1],**k)==(True,False)
    assert m.on_completed_bar(d.index[1],d.iloc[1],**k)==(False,False)
    with pytest.raises(ValueError):m.on_completed_bar(d.index[0],d.iloc[0],**k)


def test_ih_quote_callback_first_tick_order_and_level_math():
    d=fixture_bars()
    m=PinBarEMARSIStrategy(d,tail_ratio_threshold=.7,ema_short_period=2,ema_long_period=3,
                         rsi_period=2,stop_loss_ratio=.05,take_profit_ratio=.1,
                         trailing_stop_ratio=.02,provider=FixedIndicators())
    assert m.on_quote_tick(d.index[1],bid=9.9,ask=10.1) is None
    intent=m.on_quote_tick(d.index[2],bid=9.9,ask=10.1)
    assert intent.side=='BUY'
    assert intent.stop_loss==pytest.approx(9.9*.95)
    assert intent.take_profit==pytest.approx(10.1*1.1)
    assert intent.trailing_distance==pytest.approx(9.9*.02)
    assert m.on_quote_tick(d.index[2],bid=9.9,ask=10.1) is None
    assert m.on_quote_tick(d.index[3],bid=9.9,ask=10.1,has_open_order=True) is None


def test_ih_quote_bad_quotes_rejected():
    m=PinBarEMARSIStrategy(fixture_bars(),tail_ratio_threshold=.7,ema_short_period=2,ema_long_period=3,
                         stop_loss_ratio=.05,take_profit_ratio=.1,provider=FixedIndicators())
    with pytest.raises(ValueError):m.on_quote_tick(fixture_bars().index[1],bid=11,ask=10)


@pytest.mark.skipif(importlib.util.find_spec('vectorbtpro') is None,reason='Optional licensed dependency is not installed')
def test_optional_vbt_indicator_adapter():
    from atar.indicators import VBTProIndicators
    p=VBTProIndicators();d=market(bars=150)
    out=p.ema(d.close,10)
    assert out.index.equals(d.index)
    assert out.dropna().size>0


@pytest.mark.skipif(importlib.util.find_spec('vectorbtpro') is None,reason='Optional licensed dependency is not installed')
def test_original_vbt_pinbar_minute_api():
    from atar.integrations.vbtpro_pinbar import pinbaremarsi_signal
    d=market(bars=600);d.index=pd.date_range('2021-01-01',periods=len(d),freq='min',tz='UTC')
    a,_,b,_=pinbaremarsi_signal(d.open,d.high,d.low,d.close,'5min',.65,
                               (d.index[200],d.index[-1]),('00:00','23:59'))
    assert a.index.equals(d.loc[d.index[200]:].index)
    assert a.dtype==bool and b.dtype==bool
