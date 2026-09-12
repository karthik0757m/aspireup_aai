# Render deployment

Status: deployment configuration prepared; no live Render URLs verified yet.

Keep `render.yaml`, `agent_1/` and `agent_2/` at the GitHub repository root. Each project remains independent. The existing root application can remain alongside them.

## Deploy using a Blueprint

1. Sign in to Render and connect the GitHub repository containing these files.
2. Create a Blueprint from that repository. Render reads `render.yaml` and prepares two Python web services.
3. Supply `GEMINI_API_KEY` for each service using Render's secret environment fields. The same existing key can serve both agents. Do not upload `.env` to GitHub.
4. Set `DEMO_ACCESS_CODE` to a private value for evaluator access to AI mode. Offline demonstrations remain open. Share this code privately with evaluators, not in a public repository.
5. Use the configured free service plan unless you explicitly choose paid hosting. Free instances are suitable for assignment demos; they can sleep and are not an always-on production hosting guarantee.
6. Wait for both builds and health checks. Open each assigned `onrender.com` URL, run its offline demonstration, then unlock Gemini AI mode and run a synthetic example.
7. Put the verified URLs into the submission PDF. Never use the service names to guess unverified live URLs.

## Manual service settings

| Setting | FaultSense | BuildWise |
|---|---|---|
| Runtime | Python | Python |
| Root directory | agent_1 | agent_2 |
| Build command | `pip install -r requirements.txt` | `pip install -r requirements.txt` |
| Start command | `python -m streamlit run app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true --browser.gatherUsageStats false` | Same |
| Health check | `/_stcore/health` | `/_stcore/health` |
| Python version | 3.12.10 | 3.12.10 |
| Generation model | gemini-3.8-flash | gemini-3.8-flash |
| Embedding model | gemini-embedding-001 | gemini-embedding-001 |

API keys and the demo access code are environment variables, not source files. Local parent `.env` loading remains supported. On Render, AI execution requires `DEMO_ACCESS_CODE` to be configured. The code protects shared API quota with a simple application-level gate; it is not a full user-account system or distributed abuse-prevention service.

References: [Blueprint specification](https://render.com/docs/blueprint-spec), [Python version](https://render.com/docs/python-version), [Free service limitations](https://render.com/docs/free).
