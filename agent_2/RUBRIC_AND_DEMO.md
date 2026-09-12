# BuildWise — evaluation and demo guide

## Agent information

- **Problem:** Selecting components requires reconciling supply, interface, energy and cost constraints across specifications.
- **Objective:** Identify the least-cost feasible sensor-node BOM within explicitly modelled constraints.
- **Target users:** Embedded-system students, prototype designers and engineering laboratory teams.
- **Features:** Catalogue validation, combination enumeration, supply/interface checks, energy calculations, alternatives, what-if tool, cited evidence and export.
- **Technologies:** Python, Streamlit, pandas, NumPy, pypdf, requests, LangGraph.
- **LLM:** Gemini 3.8 Flash, configurable. Offline output is deterministic, not LLM-generated.
- **Tools/APIs:** Catalogue evaluation, `search_knowledge`, `inspect_calculations`, `compare_duty_cycle`, Google Gemini generateContent and batchEmbedContents.
- **RAG/vector store:** Gemini embedding-001 (768 dimensions), per-page chunks, NumPy cosine vector search. Offline lexical baseline is labelled separately.
- **Framework:** LangGraph StateGraph with a bounded conditional reasoning/tool loop.
- **Input:** Hard requirements in the form, structured CSV catalogue, PDF/TXT references and design context.
- **Output:** Feasible BOM or explicit infeasibility, cost/runtime calculations, alternatives, unresolved checks, CSV/JSON/Markdown downloads.
- **Project/GitHub link:** Add after publishing. This project has not been published.
- **Demo/video link with voice:** Add after recording. No video has been created.
- **Difference from FaultSense:** BuildWise synthesizes a proposed design through constrained enumeration; FaultSense investigates an existing machine from observed sensor readings.

## Rubric mapping — 50 marks

| Category | What to show |
|---|---|
| Problem & Objective /10 | Show a concrete device brief and measurable constraints. |
| Workflow & Tool Calling /10 | Demonstrate the solver plus model-selected retrieval/calculation tools and an active-time what-if question. |
| RAG / Embeddings /10 | Show retrieved specification passages with IDs and explain semantic embeddings and vector similarity. |
| LangGraph /10 | Explain the typed state, analysis/retrieval nodes, conditional model-tool loop and bounded execution. |
| Output, Innovation & Demo /10 | Show BOM, alternatives, battery calculation, pass/fail table, explicit infeasibility and downloadable outputs. |

Use Gemini mode to demonstrate the AI categories. Offline constraint solving is a reproducible baseline, not a substitute for the LLM and semantic-embedding demo. Scores are determined by evaluators.

## Five-minute spoken demonstration

1. **0:00–0:40:** “BuildWise chooses a component set for a battery-powered Wi-Fi temperature node. It checks explicit constraints before explaining the design.”
2. **0:40–1:20:** Show the synthetic catalogue. Set INR 3,000, seven days, a 300-second interval, five active seconds and 80% usable battery capacity.
3. **1:20–2:20:** Run Gemini mode. Show 24 combinations evaluated, four feasible and the INR 1,540 least-cost sample BOM.
4. **2:20–3:10:** Show supply, logic, interface, battery envelope and regulator-current checks. Explain the runtime formula and duty-cycle assumption.
5. **3:10–4:00:** Show Evidence and Workflow. Ask the model to compare 30 active seconds; explain that the scenario does not change baseline requirements.
6. **4:00–5:00:** Change the budget to INR 1 and rerun offline: no recommendation should be issued. Export the BOM/report and contrast the design task with FaultSense's diagnostic task.

## Useful evaluator questions

- Does it extract every specification from PDFs automatically? No. The structured catalogue is authoritative; PDF retrieval provides supporting evidence for review.
- What happens when nothing fits? It reports infeasibility and shows failed constraints without silently changing requirements.
- Is runtime guaranteed? No. It is an energy estimate with explicit assumptions, to be validated by measurements.
- Is this a complete hardware design? No. PCB, protection, charging, physical fit and detailed electrical verification remain outside the solver scope.
