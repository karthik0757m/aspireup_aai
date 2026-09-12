from pathlib import Path
import pytest
from engineering import read_sensors, analyze_sensors, offline_report
from runtime import VectorStore, read_documents, build_graph, ProviderError

ROOT = Path(__file__).parent
LIMITS = dict(temperature_c=80, vibration_mm_s=4.5, current_a=12)

def sensors():
    return read_sensors((ROOT/'sample_data/motor_readings.csv').read_bytes())

def test_hot_motor():
    result = analyze_sensors(sensors(), LIMITS)
    assert result['metrics']['temperature_c']['limit_exceedances'] > 0
    assert result['metrics']['vibration_mm_s']['limit_exceedances'] > 0
    assert 'load' in result['hypotheses_in_rule_priority_order'][0]['hypothesis']

def test_healthy_and_constant_baseline():
    df = sensors()
    for column, value in [('temperature_c',50),('vibration_mm_s',1),('current_a',5),('rpm',1500)]:
        df[column] = value
    r = analyze_sensors(df, LIMITS)
    assert r['anomaly_count'] == 0
    df.loc[30,'vibration_mm_s'] = 20
    assert analyze_sensors(df,LIMITS)['anomaly_count'] == 1

@pytest.mark.parametrize('kind', ['missing','nan','duplicate','negative'])
def test_reject_bad_input(kind):
    df = sensors()
    if kind == 'missing': df = df.drop(columns='rpm')
    if kind == 'nan': df.loc[0,'current_a'] = float('nan')
    if kind == 'duplicate': df.loc[1,'timestamp'] = df.loc[0,'timestamp']
    if kind == 'negative': df.loc[0,'rpm'] = -1
    with pytest.raises(ValueError): read_sensors(df.to_csv(index=False).encode())

def store():
    return VectorStore(read_documents([('manual.txt', b'Motor vibration can indicate bearing wear. Check bearing vibration spectrum. Cooling airflow affects temperature.')]))

def test_retrieval_and_offline_graph():
    vector = store()
    assert vector.search('bearing vibration')[0]['id'] == 'S1'
    g = build_graph(lambda: analyze_sensors(sensors(),LIMITS),vector,'bearing vibration','FaultSense',offline_report)
    r = g.invoke({})
    assert 'Offline demo' in r['report'] and 'manual.txt' in r['report']
    assert r['trace'][-1].startswith('Finalize')

class FakeModel:
    def generate(self, contents, declarations, final=False):
        if len(contents) == 1:
            return {'role':'model','parts':[{'functionCall':{'name':'inspect_calculations','args':{}}}]}
        return {'role':'model','parts':[{'text':'Review bearing evidence [S1].'}]}

def test_real_graph_tool_routing_with_mock_provider():
    g=build_graph(lambda: {'ok':True},store(),'bearing','Test',str,FakeModel())
    r=g.invoke({})
    assert r['rounds'] == 2
    assert 'Tool executed: inspect_calculations' in r['trace']
    assert '[S1]' in r['report']

def test_unknown_citation_withheld():
    class BadModel:
        def generate(self,*a,**kw):
            return {'role':'model','parts':[{'text':'Invented claim [S1, S999].'}]}
    r=build_graph(lambda: {},store(),'bearing','Test',str,BadModel()).invoke({})
    assert 'withheld' in r['report']
    assert '[S999]' not in r['report']

def test_tool_loop_bounded():
    class LoopModel:
        def generate(self,*a,**kw):
            return {'role':'model','parts':[{'functionCall':{'name':'inspect_calculations','args':{}}}]}
    with pytest.raises(ProviderError, match='bounded'):
        build_graph(lambda:{},store(),'bearing','Test',str,LoopModel()).invoke({}, {'recursion_limit':20})

def test_empty_reference_rejected():
    with pytest.raises(ValueError): read_documents([('empty.txt', b'')])
