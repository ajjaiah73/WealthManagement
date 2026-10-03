# End-to-End Test Plan — Super Advisory Intelligence Platform

## 1. Scope

This plan covers the full running system:

- **Backend:**
  - JWT auth and roles.
  - The LangGraph pipeline, with Claude agents for intent, synthesis and narrative.
  - Hybrid retrieval: Qdrant dense + BM25 + Neo4j/networkx graph, with RRF and cross-encoder rerank.
  - The deterministic/Z3 compliance engine.
  - The self-correction loop.
  - Append-only audit persistence via SQLAlchemy on SQLite or PostgreSQL.
  - The SSE agent stream and report generation.
- **Frontend:** login plus the 11 sections of the React UI.

| Layer | Command | What it covers |
|---|---|---|
| Unit / integration (offline) | `cd backend && .venv/Scripts/python.exe -m pytest -q` | Compliance rules, the LangGraph pipeline with a fake LLM (override attempts, critique feedback, fallback, terminal-status ordering), RRF/BM25/graph retrieval and the hybrid retriever with real models, append-only DB triggers, SQL repositories, JWT auth and roles, token redaction in access logs, API smoke tests, fact-find validation |
| End-to-end (live servers) | `cd backend && .venv/Scripts/python.exe scripts/e2e_test.py [--api URL] [--web URL]` | Every test ID in §3 except the `UI-*` manual checks; makes real Claude calls when the LLM is enabled |
| Static | `ruff check app tests scripts`, `mypy app`, `cd frontend && npm run build && npm run lint` | Lint, types, TS compile |
| Infrastructure | `docker-compose up -d`, then run the backend with Postgres/Qdrant/Neo4j URLs (README, Option B) and rerun e2e with `--api` | Same e2e suite against real Postgres, Qdrant server and Neo4j |

## 2. Environment

| Component | URL | Start command |
|---|---|---|
| Backend | http://localhost:8010 | `env -u ANTHROPIC_BASE_URL -u ANTHROPIC_AUTH_TOKEN -u ANTHROPIC_API_KEY .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010` |
| Frontend | http://localhost:5174 | `npx vite --port 5174 --strictPort` |
| Infra (optional) | Postgres :55432, Qdrant :56333, Neo4j :57474/:57687 | `docker-compose up -d` |
| Containerised app (optional) | UI :8081, API :58010 | `docker-compose --profile app up -d --build` |

The `ANTHROPIC_API_KEY` lives only in `backend/.env`. The e2e suite logs in as the demo `advisor` (and as `compliance` for the role checks).

## 3. Test cases

### 3.1 Health, auth and reference data
| ID | Test | Expected |
|---|---|---|
| API-01 | `GET /api/health` | 200; `demo_mode`, `orchestrator=langgraph`, `auth_enabled`, `max_iterations=3` |
| RET-00 | Hybrid retrieval components | `ready=true`; dense, BM25, graph, reranker and RRF are all present; no component errors |
| AUTH-01 | Protected API with no token / a forged token | 401 / 401 |
| AUTH-02 | Wrong password / unknown user | 401 with an identical message for both (no user enumeration) |
| AUTH-03 | Advisor login + `/api/auth/me` | Token issued with an expiry; `/me` returns the advisor role |
| AUTH-04 | Compliance officer | Reads 200; `run`, `start` and fact-find writes return 403 |
| API-02..04 | List clients / products / documents | 10 / 13 / 20 unique |
| API-05 | Client detail + fact-find for every client | 200; every field is `present` or `missing` |
| API-06 | Document detail for every document | 200 |
| API-07 | Product fees | Total fee in (0, 5)% |

### 3.2 Demo scenarios (run via `POST /api/advisory/start` → live SSE stream)
| ID | Client | Expected status | Iterations | What it proves |
|---|---|---|---|---|
| SCN-01 | C-0001 | COMPLIANT | 1 | Clean pass |
| SCN-02 | C-0002 | COMPLIANT | 2–3 | Self-correction: rejected draft → critique → re-synthesis |
| SCN-03 | C-0004 | REQUIRES_HUMAN_REVIEW | 3 | Escalation after max iterations (CONTRIB-001: $32,000 > $30,000 cap) |
| SCN-04 | C-0006 | WARNING | 1 | FEE-001 (1.90% > 1.75%), ALLOC-002 (defensive allocation < 25% for an over-55) |
| SCN-05 | — | The SSE `done` payload equals the later GET; cases are listed | — | Persistence round-trip; no early `done` before the narrative is written |
| SCN-06 | All 10 | 201 for every client, no 5xx, no case left IN_PROGRESS | — | No crashes on incomplete fact-finds |

### 3.3 Orchestration, retrieval, compliance, audit, LLM, reports
| ID | Test | Expected |
|---|---|---|
| SSE-02 | Live streaming | Nodes arrive in the order intent → hybrid_retrieval → synthesize; the critique is streamed; with the LLM enabled, events arrive over more than 1s (not one burst) |
| RET-01 | Retrieved evidence | `retrieval_method=fused`, ranks 1..n, RRF and rerank scores present; dense, BM25 and graph sources all seen; graph context and retrieval query recorded |
| ORC-01 | `GET /api/advisory/graph` | The compiled LangGraph mermaid contains intent/retrieval/synthesis/compliance/critique/escalate/narrate |
| CMP-01 | Compliance per scenario | COMPLIANT/COMPLIANT/REJECTED/WARNING; `passed + failed + warnings = evaluated`; the expected failed rule is present; disclosures are not empty |
| AUD-01 | Audit trail C-0002 | `structured_critique` present; the highest iteration equals `iteration_count`; timestamps are ordered; the global audit is a superset of the case audit |
| LLM-01 | Narrative | `llm_narrative` with a model for C-0001; **none** for the REQUIRES_HUMAN_REVIEW case |
| LLM-02 | Claude agents | Intent is `[llm]`; synthesis method recorded; C-0004 still escalates even though Claude chose its products (the LLM cannot override rules) |
| SSE-01 | Stream for a completed case | `text/event-stream`; one `data:` per audit event, then `event: done` |
| RPT-01 | Generate a SoA for each scenario | 200, `is_demo_data=true`, matching client, non-empty summary |

### 3.4 Edge cases and error handling
| ID | Test | Expected |
|---|---|---|
| EDG-01..03 | Unknown client: detail / fact-find / advisory run | 404 |
| EDG-04 | Advisory run without `client_id` | 422 |
| EDG-04b | Background `start` for an unknown client | 404 |
| EDG-05..08 | Unknown case: GET / stream / compliance / report | 404 |
| EDG-09 | Unknown document | 404 |
| EDG-10 | Fact-find update for an unknown client | 404 |
| EDG-11 | Fact-find update with the wrong type | 422 |
| EDG-12 | Fact-find update with an unknown field | 422 |
| EDG-13 | Fact-find update changing `client_id` | 422 |
| EDG-14 | Create an existing client | 409 |
| EDG-15 / 16 | Unknown route / wrong method | 404 / 405 |
| EDG-17 | Audit trail for an unknown case | 200 `[]` |
| EDG-18 / 19 | A valid update persists; rejected updates leave the profile intact | — |

### 3.5 Security and frontend
| ID | Test | Expected |
|---|---|---|
| SEC-01 / 02 | CORS preflight from the frontend / a foreign origin | Allowed / rejected |
| SEC-03 | Key exposure | No `sk-ant` in health, OpenAPI, login, `/me`, audit, case list or frontend-served files |
| WEB-01 | Deep links, including `/login` and an unknown route | 200 SPA shell |
| WEB-02 | Route wiring | All 11 section components, the login route + `RequireAuth` guard, and the `*` 404 route |

Infrastructure checks, done manually with `docker exec … psql` / `cypher-shell`:

- `UPDATE`, `DELETE` and `TRUNCATE` on `audit_events` all fail with `audit_events is append-only`.
- Neo4j contains the Document, Product, Topic and ProductType nodes.
- `/api/health` reports `postgresql`, `qdrant-server` and `neo4j`.

### 3.6 Manual visual checklist (browser)
| ID | Section | Check |
|---|---|---|
| UI-00 | Login | Unauthenticated deep link redirects to `/login?next=…`; demo-account cards fill the form; a bad password shows an error; logout returns to login |
| UI-01 | Dashboard | KPI tiles match case counts; recent cases link through |
| UI-02 | Clients / Client Detail | Search filters; a row opens the detail view; fact-find completion is shown |
| UI-03 | Fact Find | Missing fields highlighted (e.g. C-0003) |
| UI-04 | Advisory Workspace | Run C-0001/2/4/6. The timeline streams node by node while the status shows "In Progress"; the final status and iterations match §3.2; for C-0002 the critique card is shown; Retrieved Evidence shows dense/BM25/graph badges, RRF and rerank scores, and graph paths |
| UI-04b | Role gating | As `compliance`, the Run button is disabled with a read-only notice |
| UI-05 | Agent Execution | Timeline for any case; C-0002 shows the critique, then re-synthesis |
| UI-06 | Compliance | C-0004 shows CONTRIB-001 failed; C-0006 shows warnings in amber |
| UI-07 | Products | Type filter and fee sort work; an empty search shows the empty state |
| UI-08 | Documents | Search plus detail panel |
| UI-09 | Reports | Generate a SoA; DEMO DATA badge visible |
| UI-10 | Audit Trail | Agent/status filters; the case link opens Agent Execution |
| UI-11 | Settings | Live orchestrator, LLM agents, persistence, and the retrieval component list from `/api/health` |
| UI-12 | Unknown route | 404 page with "Back to Dashboard" |
| UI-13 | Backend stopped | Pages show error states; no blank screen |

## 4. Exit criteria

- All pytest, ruff, mypy, build and lint checks pass.
- `scripts/e2e_test.py` exits 0 against both the SQLite and the Postgres/Qdrant/Neo4j backends.
- The UI checklist has been reviewed.
