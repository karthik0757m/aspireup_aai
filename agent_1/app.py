"""Run with: python -m streamlit run app.py"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from engineering import METRICS, read_sensors, analyze_sensors, offline_report
from runtime import Gemini, ProviderError, VectorStore, read_documents, build_graph
from access import require_ai_access

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='FaultSense | Engineering diagnostics', page_icon='⚙️', layout='wide')
st.markdown('''<style>.stApp {background:#f5f8fc} h1,h2,h3{color:#142d4e}
div.stButton>button[kind="primary"]{background:#176b87;border:0}
[data-testid="stMetric"]{background:white;padding:16px;border-radius:12px}</style>''', unsafe_allow_html=True)
st.caption('AGENT 01 / CONDITION MONITORING')
st.title('FaultSense')
st.write('Turn machine readings into an evidence-backed investigation.')

with st.sidebar:
    st.header('Run settings')
    mode = st.radio('Analysis mode', ['Offline demo', 'Gemini AI'])
    st.caption('Offline: lexical retrieval + rule-based screening. Gemini: semantic embeddings + LLM tool calling.')
    if mode == 'Gemini AI':
        st.info('Reference text, your request and computed readings are sent to Google Gemini. The key is read from your local .env.')
        access_code = st.text_input('Evaluator access code (if configured)', type='password')
    st.subheader('Operating limits')
    st.caption('Demo values only. Enter limits from your machine documentation for real data.')
    temp = st.number_input('Temperature limit (°C)', min_value=1.0, value=80.0)
    vibration = st.number_input('Vibration limit (mm/s RMS)', min_value=0.01, value=4.5)
    current = st.number_input('Current limit (A)', min_value=0.01, value=12.0)
    st.divider()
    st.download_button('Download sample sensor CSV', (ROOT/'sample_data/motor_readings.csv').read_bytes(), 'motor_readings.csv')
    st.download_button('Download demo reference', (ROOT/'sample_data/maintenance_guide.txt').read_bytes(), 'maintenance_guide.txt')

left, right = st.columns([1, 1])
with left:
    st.subheader('1 · Machine observations')
    sample = st.checkbox('Use the included motor demonstration', value=True)
    csv = st.file_uploader('Sensor readings (.csv)', type=['csv'])
    prompt = st.text_area('Describe the symptoms or investigation', 'The motor gets hot and vibrates under load. Investigate overload, bearing and cooling issues; recommend diagnostic checks.', height=130)
with right:
    st.subheader('2 · Reference evidence')
    docs = st.file_uploader('Maintenance manuals (.pdf or .txt)', type=['pdf', 'txt'], accept_multiple_files=True)
    st.caption('PDFs need selectable text. Source filenames and page numbers are preserved.')
    st.info('Demo data and the reference guide are synthetic educational examples, not manufacturer specifications.')

if st.button('Analyze machine', type='primary'):
    st.session_state.pop('run', None)
    try:
        if mode == 'Gemini AI':
            require_ai_access(access_code)
        if not prompt.strip():
            raise ValueError('Describe the investigation first.')
        data = csv.getvalue() if csv else (ROOT/'sample_data/motor_readings.csv').read_bytes() if sample else None
        if data is None:
            raise ValueError('Upload readings or enable the demo.')
        frame = read_sensors(data)
        files = [(f.name, f.getvalue()) for f in docs]
        if not files and sample:
            files = [('maintenance_guide.txt', (ROOT/'sample_data/maintenance_guide.txt').read_bytes())]
        with st.status('Investigating readings and references…', expanded=True) as status:
            provider = Gemini() if mode == 'Gemini AI' else None
            store = VectorStore(read_documents(files), provider)
            limits = {'temperature_c': temp, 'vibration_mm_s': vibration, 'current_a': current}
            graph = build_graph(lambda: analyze_sensors(frame, limits), store, prompt, 'FaultSense', offline_report, provider)
            result = graph.invoke({}, {'recursion_limit': 20})
            status.update(label='Investigation complete', state='complete', expanded=False)
        st.session_state.run = (result, frame, mode, limits)
    except (ValueError, ProviderError) as exc:
        st.error(str(exc))
    except Exception:
        st.error('Unexpected analysis failure. Check the input format and installed dependency versions. No result was substituted.')

if 'run' in st.session_state:
    run, frame, run_mode, limits = st.session_state.run
    result = run['result']
    st.caption(f'Completed run: {run_mode}. Changed inputs apply when you click Analyze machine again.')
    a, b, c = st.columns(3)
    a.metric('Readings analyzed', result['rows'])
    b.metric('Flagged metric observations', result['anomaly_count'])
    c.metric('Peak temperature', f"{result['metrics']['temperature_c']['maximum']} °C")
    report, charts, evidence, workflow = st.tabs(['Diagnostic report', 'Sensor trends', 'Evidence', 'Workflow'])
    with report:
        st.markdown(run['report'].split('## Retrieved evidence')[0])
        st.download_button('Download complete report', run['report'], 'faultsense_report.md', 'text/markdown')
        st.download_button('Download analysis JSON', json.dumps(run['result'], indent=2), 'faultsense_analysis.json', 'application/json')
    with charts:
        for metric, unit in METRICS.items():
            st.write(f'**{metric} ({unit})**')
            plot = frame.set_index('timestamp')[[metric]].copy()
            if metric in limits:
                plot['Operating limit'] = limits[metric]
            st.line_chart(plot)
        st.dataframe(pd.DataFrame(result['anomalies']), hide_index=True, width='stretch')
    with evidence:
        if not run['evidence']:
            st.warning('No relevant reference passages were retrieved.')
        for e in run['evidence']:
            with st.expander(f"[{e['id']}] {e['source']} · page {e['page']} · similarity {e['similarity']}"):
                st.write(e['text'])
        st.caption('Similarity is retrieval relevance, not confidence that a fault exists.')
    with workflow:
        st.code('\n↓\n'.join(run['trace']), language=None)
        st.json(result)
