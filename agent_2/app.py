"""Run with: python -m streamlit run app.py --server.port 8502"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from engineering import read_catalog, evaluate_catalog, offline_report
from runtime import Gemini, ProviderError, VectorStore, read_documents, build_graph
from access import require_ai_access

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='BuildWise | Component engineering', page_icon='🔧', layout='wide')
st.markdown('''<style>.stApp {background:#f8f7f2} h1,h2,h3{color:#234139}
div.stButton>button[kind="primary"]{background:#327761;border:0}
[data-testid="stMetric"]{background:white;padding:16px;border-radius:12px}</style>''', unsafe_allow_html=True)
st.caption('AGENT 02 / CONSTRAINT-DRIVEN DESIGN')
st.title('BuildWise')
st.write('Select a sensor-node bill of materials. Check every modelled constraint.')

with st.sidebar:
    st.header('Design requirements')
    mode = st.radio('Analysis mode', ['Offline demo', 'Gemini AI'])
    if mode == 'Gemini AI':
        st.info('Reference text, requirements and computed catalogue results are sent to Google Gemini. Your key stays in local configuration.')
        access_code = st.text_input('Evaluator access code (if configured)', type='password')
    budget = st.number_input('BOM budget (INR)', min_value=1.0, value=3000.0)
    days = st.number_input('Target runtime (days)', min_value=0.1, value=7.0)
    interval = st.number_input('Measurement interval (seconds)', min_value=1.0, value=300.0)
    active = st.number_input('Active time per cycle (seconds)', min_value=0.01, value=5.0)
    usable = st.slider('Usable battery capacity (%)', 10, 100, 80)
    wifi = st.checkbox('Wi-Fi required', value=True)
    st.caption('The form defines hard constraints. Describe additional preferences below; unmodelled constraints remain open checks.')
    st.divider()
    st.download_button('Download catalogue template', (ROOT/'sample_data/components.csv').read_bytes(), 'components.csv')
    st.download_button('Download demo datasheets', (ROOT/'sample_data/datasheets.txt').read_bytes(), 'datasheets.txt')

left, right = st.columns(2)
with left:
    st.subheader('1 · Define your device')
    prompt = st.text_area('Design description and preferences', 'Design a battery-powered Wi-Fi temperature monitoring node. Compare compatible controller, sensor, battery and regulator options and explain runtime tradeoffs.', height=130)
    sample = st.checkbox('Use the included component demonstration', value=True)
    catalog = st.file_uploader('Component catalogue (.csv)', type=['csv'])
with right:
    st.subheader('2 · Add specification evidence')
    docs = st.file_uploader('Datasheets (.pdf or .txt)', type=['pdf', 'txt'], accept_multiple_files=True)
    st.info('Included parts, prices and datasheets are synthetic teaching examples. Replace them with verified catalogue entries for an actual design.')
    st.caption('Scope: one controller, digital temperature sensor, battery and regulator. No live supplier pricing.')

if st.button('Evaluate designs', type='primary'):
    st.session_state.pop('run', None)
    try:
        if mode == 'Gemini AI':
            require_ai_access(access_code)
        if not prompt.strip():
            raise ValueError('Describe the design first.')
        data = catalog.getvalue() if catalog else (ROOT/'sample_data/components.csv').read_bytes() if sample else None
        if data is None:
            raise ValueError('Upload a catalogue or enable the demonstration.')
        frame = read_catalog(data)
        req = dict(budget_inr=budget, runtime_days=days, interval_s=interval, active_s=active, usable_fraction=usable/100, wifi=wifi)
        # Validate constraints before creating paid embeddings.
        baseline = evaluate_catalog(frame, req)
        files = [(f.name, f.getvalue()) for f in docs]
        if not files and sample:
            files = [('datasheets.txt', (ROOT/'sample_data/datasheets.txt').read_bytes())]
        with st.status('Checking combinations and supporting evidence…', expanded=True) as status:
            provider = Gemini() if mode == 'Gemini AI' else None
            store = VectorStore(read_documents(files), provider)
            def scenario(active_seconds):
                changed = dict(req, active_s=active_seconds)
                r = evaluate_catalog(frame, changed)
                return {'scenario_active_s': active_seconds, 'status': r['status'], 'recommended': r['recommended']}
            extra = {'compare_duty_cycle': ({'name': 'compare_duty_cycle',
                'description': 'Evaluate a what-if active duration without changing the original design requirements.',
                'parameters': {'type': 'OBJECT', 'properties': {'active_seconds': {'type': 'NUMBER'}}, 'required': ['active_seconds']}}, scenario)}
            graph = build_graph(lambda: baseline, store, prompt, 'BuildWise', offline_report, provider, extra)
            result = graph.invoke({}, {'recursion_limit': 20})
            status.update(label='Design evaluation complete', state='complete', expanded=False)
        st.session_state.run = (result, mode)
    except (ValueError, ProviderError) as exc:
        st.error(str(exc))
    except Exception:
        st.error('Unexpected design evaluation failure. Check inputs and dependency versions. No result was substituted.')

if 'run' in st.session_state:
    run, run_mode = st.session_state.run
    result = run['result']
    st.caption(f'Completed run: {run_mode}. Click Evaluate designs to apply changed inputs.')
    a, b, c = st.columns(3)
    a.metric('Combinations checked', result['combinations_evaluated'])
    b.metric('Feasible combinations', result['feasible_count'])
    selected = result['recommended']
    c.metric('Recommended BOM', f"INR {selected['cost_inr']:.0f}" if selected else 'None feasible')
    report, design, evidence, workflow = st.tabs(['Design report', 'BOM & alternatives', 'Evidence', 'Workflow'])
    with report:
        st.markdown(run['report'].split('## Retrieved evidence')[0])
        st.download_button('Download complete report', run['report'], 'buildwise_report.md', 'text/markdown')
        st.download_button('Download analysis JSON', json.dumps(result, indent=2), 'buildwise_analysis.json', 'application/json')
    with design:
        if selected:
            st.subheader('Recommended bill of materials')
            bom = pd.DataFrame(selected['bom'])
            st.dataframe(bom, hide_index=True, width='stretch')
            st.download_button('Download BOM CSV', bom.to_csv(index=False), 'buildwise_bom.csv', 'text/csv')
            st.write(f"Estimated runtime: **{selected['runtime_days']} days**")
            st.dataframe(pd.DataFrame([{'Constraint': k, 'Status': 'PASS' if v else 'FAIL'} for k,v in selected['checks'].items()]), hide_index=True)
        else:
            st.warning('No feasible design. The alternatives below fail one or more original requirements.')
        for i, alt in enumerate(result['alternatives'], 1):
            with st.expander(f"Alternative {i} · INR {alt['cost_inr']} · {alt['runtime_days']} days · {'PASS' if alt['feasible'] else 'FAIL'}"):
                st.json(alt)
    with evidence:
        for e in run['evidence']:
            with st.expander(f"[{e['id']}] {e['source']} · page {e['page']} · similarity {e['similarity']}"):
                st.write(e['text'])
        st.caption('Catalogue specifications are not automatically certified by these retrieved passages.')
    with workflow:
        st.code('\n↓\n'.join(run['trace']), language=None)
        st.json(result)
