import json
from pathlib import Path
import pandas as pd
import pytest
from atar.demo import run_demo, DEFAULT_CONFIG


def small_config():
    cfg=json.loads(json.dumps(DEFAULT_CONFIG))
    cfg['bars']=700
    cfg['windows']={'warmup':120,'train':220,'validation':160,'final':160,'step':160}
    return cfg


def test_complete_demo_resume_and_changed_config(tmp_path):
    out=tmp_path/'run'
    first=run_demo(out,small_config())
    assert first['identical_shortlists']
    assert (out/'report.html').is_file()
    assert json.loads((out/'run.json').read_text())['status']=='COMPLETE'
    second=run_demo(out,small_config())
    assert all(row['actual_simulations']==0 for row in second['selection_counts'])
    assert first['avoided_evaluations']==second['avoided_evaluations']
    cfg=small_config();cfg['seed']+=1
    with pytest.raises(ValueError):run_demo(out,cfg)


def test_empty_shortlist_is_success_not_gate_relaxation(tmp_path):
    cfg=small_config();cfg['train_gate']['min_trades']=100000
    out=tmp_path/'run';result=run_demo(out,cfg)
    assert result['final_rows']==0
    assert pd.read_csv(out/'final_evaluation.csv').empty
    assert all(row['shortlist_count']==0 for row in result['selection_counts'])


def test_arbitrary_output_and_symlink_refused(tmp_path):
    out=tmp_path/'run';out.mkdir();(out/'personal.txt').write_text('unchanged')
    with pytest.raises(ValueError):run_demo(out,small_config())
    assert (out/'personal.txt').read_text()=='unchanged'
    link=tmp_path/'linked';link.symlink_to(out,target_is_directory=True)
    with pytest.raises(ValueError):run_demo(link,small_config())
