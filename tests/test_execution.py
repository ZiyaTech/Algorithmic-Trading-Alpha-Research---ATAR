import numpy as np
import pandas as pd
import pytest
from atar.backends.reference import Execution, simulate
from atar.temporal import Window
from atar.strategies.common import Signals


def bars(rows):
    return pd.DataFrame(rows,columns=['open','high','low','close'],
                        index=pd.date_range('2021-01-01',periods=len(rows),freq='h',tz='UTC'))


def run(d,side=1,**kwargs):
    a=pd.Series(False,index=d.index);b=a.copy()
    (a if side==1 else b).iloc[0]=True
    w=Window('test',d.index[0],d.index[-1]+pd.Timedelta(hours=1))
    return simulate(d,Signals(a,b),w,Execution(cost_bps_per_side=0,**kwargs))


@pytest.mark.parametrize('side',[1,-1])
def test_ambiguous_bar_uses_stop_first(side):
    d=bars([[100,101,99,100],[100,120,80,100],[100,101,99,100]])
    r=run(d,side,stop_loss=.1,take_profit=.1)
    assert r['trades'][0]['entry_time']==d.index[1].isoformat()
    assert r['trades'][0]['net_return']==pytest.approx(-.1)
    assert r['trades'][0]['exit_reason']=='stop'


@pytest.mark.parametrize('side',[1,-1])
def test_gap_stop_fills_at_open(side):
    last=[80,82,78,81] if side==1 else [120,122,118,121]
    d=bars([[100,101,99,100],[100,101,99,100],last])
    r=run(d,side,stop_loss=.05,take_profit=.1)
    assert r['trades'][0]['net_return']==pytest.approx(-.2)
    assert r['trades'][0]['exit_reason']=='gap_stop'


def test_stage_forced_exit_no_later_price():
    d=bars([[100,101,99,100],[100,103,99,102],[200,210,190,200]])
    a=pd.Series([True,False,False],index=d.index)
    r=simulate(d,Signals(a,a & False),Window('train',d.index[0],d.index[2]),Execution(stop_loss=.2,take_profit=.5,cost_bps_per_side=1))
    assert r['trades'][0]['exit_reason']=='window_end'
    assert r['trades'][0]['net_return']==pytest.approx(.02-.0002)
    assert r['trades'][0]['exit_price']==102


def test_no_previous_stage_signal_carry():
    d=bars([[100,101,99,100]]*4)
    a=pd.Series([True,False,False,False],index=d.index)
    r=simulate(d,Signals(a,a & False),Window('validation',d.index[1],d.index[-1]+pd.Timedelta(hours=1)),Execution())
    assert r['metrics']['trades_count']==0
    assert r['metrics']['profit_factor'] is None


def test_conflicting_signals_and_bad_window_rejected():
    d=bars([[100,101,99,100]]*3);a=pd.Series(True,index=d.index)
    w=Window('x',d.index[0],d.index[-1]+pd.Timedelta(hours=1))
    with pytest.raises(ValueError):simulate(d,Signals(a,a),w,Execution())
    with pytest.raises(ValueError):simulate(d,Signals(a,a & False),Window('x',d.index[0]-pd.Timedelta(hours=1),w.end),Execution())


@pytest.mark.parametrize('field,value',[('stop_loss',0),('take_profit',1),('max_holding_bars',True),('cost_bps_per_side',float('nan'))])
def test_execution_rejects_bad_settings(field,value):
    with pytest.raises(ValueError):Execution(**{field:value})
