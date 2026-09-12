from pathlib import Path
import pytest
from engineering import read_catalog, evaluate_catalog, offline_report
from runtime import VectorStore, read_documents, build_graph

ROOT=Path(__file__).parent
REQ=dict(budget_inr=3000.,runtime_days=7.,interval_s=300.,active_s=5.,usable_fraction=.8,wifi=True)
def catalog(): return read_catalog((ROOT/'sample_data/components.csv').read_bytes())

def test_valid_design():
    r=evaluate_catalog(catalog(),REQ)
    assert r['feasible_count'] > 0
    assert all(r['recommended']['checks'].values())
    assert r['recommended']['cost_inr'] <= REQ['budget_inr']

def test_impossible_budget_not_relaxed():
    r=evaluate_catalog(catalog(),dict(REQ,budget_inr=1))
    assert r['recommended'] is None
    assert all('budget' in a['failed_constraints'] for a in r['alternatives'])

def test_impossible_runtime():
    r=evaluate_catalog(catalog(),dict(REQ,runtime_days=100000))
    assert r['recommended'] is None

def test_incompatible_parts_excluded():
    r=evaluate_catalog(catalog(),REQ)
    for design in [r['recommended'],*r['alternatives']]:
        assert 'TEMP-X5' not in [p['part_id'] for p in design['bom']]
        assert 'REG-HI' not in [p['part_id'] for p in design['bom']]

def test_runtime_formula_against_hand_calculation():
    df=catalog()
    df=df[df.part_id.isin(['CTRL-W1','TEMP-I1','BAT-2A','REG-BB'])]
    r=evaluate_catalog(df,REQ)['recommended']
    average=181*(5/300)+.082*(295/300)
    input_mw=3.3*average/.9+3.7*.03
    days=(2*3.7*.8)*1000/input_mw/24
    assert r['runtime_days'] == round(days,2)

@pytest.mark.parametrize('change',[{'active_s':301},{'usable_fraction':1.2},{'budget_inr':float('nan')},{'runtime_days':0}])
def test_invalid_requirements(change):
    with pytest.raises(ValueError): evaluate_catalog(catalog(),dict(REQ,**change))

def test_unknown_specs_rejected():
    df=catalog(); df.loc[0,'logic_v']=float('nan')
    with pytest.raises(ValueError): read_catalog(df.to_csv(index=False).encode())

def test_out_of_stock():
    df=catalog(); df.loc[df.category == 'battery','stock']=0
    with pytest.raises(ValueError): evaluate_catalog(df,REQ)

def test_offline_graph():
    store=VectorStore(read_documents([('specs.txt',b'Battery regulator supply voltage and controller WiFi duty cycle.')]))
    r=build_graph(lambda:evaluate_catalog(catalog(),REQ),store,'battery regulator','BuildWise',offline_report).invoke({})
    assert r['result']['recommended']
    assert 'specs.txt' in r['report']
