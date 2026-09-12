# FaultSense — evaluation and demo guide

## Agent information

- **Problem:** Machine readings and maintenance references are disconnected, slowing evidence-based fault investigation.
- **Objective:** Detect unusual measurements and produce traceable investigation priorities.
- **Target users:** Engineering students, maintenance analysts and laboratory teams.
- **Features:** Validated CSV input, limit checks, robust deviations, hypothesis screening, cited retrieval, sensor charts, visible tool calls and report export.
- **Technologies:** Python, Streamlit, NumPy, pandas, pypdf, requests, LangGraph.
- **LLM:** Gemini 3.8 Flash, configurable. Offline mode is not an LLM.
- **Tools/APIs:** Sensor analysis, `search_knowledge`, `inspect_calculations`, Google Gemini generateContent and batchEmbedContents.
- **RAG/vector store:** Gemini embedding-001, 768 dimensions, in-memory NumPy cosine vector store. Per-page chunk metadata. Offline lexical baseline clearly labelled.
- **Framework:** LangGraph StateGraph with conditional model/tool routing.
- **Input:** Timestamped sensor CSV, reference PDFs/TXT, user operating limits and symptom description.
- **Output:** Screening hypotheses, source passages, trend charts, anomaly records and Markdown/JSON reports.
- **Project/GitHub link:** Add after publishing; no repository has been created or published by this build.
- **Demo/video link with voice:** Add after recording; no video is claimed to exist.
- **Difference from BuildWise:** FaultSense investigates observations from an existing machine. BuildWise enumerates and validates components for a proposed sensor-node design.

## Rubric mapping — 50 marks

| Category | What to show |
|---|---|
| Problem & Objective /10 | Explain the investigation task and why raw readings are insufficient to confirm a root cause. |
| Workflow & Tool Calling /10 | Run Gemini mode and show the Workflow tab, registered tools and model/tool round trips. |
| RAG / Embeddings /10 | Upload or use the reference, show source/page IDs, explain document/query embeddings and cosine retrieval. |
| LangGraph /10 | Open `runtime.py` and explain state, graph nodes, conditional routing, bounded loops and failure handling. |
| Output, Innovation & Demo /10 | Demonstrate charts, transparent hypotheses, source evidence, report export and malformed-input handling. |

Coverage is not a guaranteed score. Use live Gemini mode for the LLM/semantic-embedding portions; use offline mode only to explain the deterministic baseline.

## Five-minute spoken demonstration

1. **0:00–0:40:** “FaultSense helps investigate machine behavior. It provides hypotheses and evidence, not an automatic fault verdict.”
2. **0:40–1:20:** Show the synthetic motor CSV, units, demo limits and maintenance text. Explain that real equipment needs verified limits.
3. **1:20–2:20:** Select Gemini AI and run. Explain that the same key provides semantic embeddings and generation.
4. **2:20–3:10:** Show the 60 readings, 27 flagged metric observations and peak temperature 86.81 C in the sample. Multiple metrics at one timestamp count separately.
5. **3:10–4:00:** Open Evidence and Workflow. Point out the tool names and source IDs. Explain why vibration alone cannot confirm a bearing fault.
6. **4:00–5:00:** Export the report, show tests, and explain the distinction from BuildWise. Mention missing waveforms/healthy baseline as future work.

## Useful evaluator questions

- Why RAG? It retrieves relevant reference passages rather than relying solely on model memory.
- Why tools? Numerical results are computed by validated Python functions and returned as model evidence.
- Why LangGraph? It exposes the investigation steps and bounds repeated model/tool calls.
- Can it guarantee a diagnosis? No. It produces screening hypotheses, identifies evidence gaps and suggests checks.
