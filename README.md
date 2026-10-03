# Autonomous Multi-Agent Neuro-Symbolic Framework for Superannuation Advisory & Regulatory Compliance Verification

Enterprise agentic-AI platform for Australian superannuation advice. A **LangGraph** multi-agent
pipeline (intent extraction → hybrid retrieval → advisory synthesis → neuro-symbolic compliance
verification → self-correction) produces recommendations. A **deterministic compliance engine**
(Pydantic rules + Z3 SMT solver) verifies every recommendation. Its verdict is authoritative: LLM output
can never override a failed rule. Rejected drafts get a structured critique and are re-synthesised, up to
`MAX_ITERATIONS=3`. After that, the case is escalated to `REQUIRES_HUMAN_REVIEW`. Every agent step is
written to an append-only audit trail.

> **DEMO MODE:** clients, products and regulatory documents are **synthetic** (10 clients, 13 products,
> 20 documents) and are labelled as such in the UI and in generated Statements of Advice. Everything
> that processes that data is real: the LangGraph runtime, Claude calls, hybrid retrieval, the Z3 compliance engine,
> the database persistence and the JWT auth. No external advice platform, product feed or registry is integrated.

## Architecture

| Layer | Implementation | Fallback when unconfigured |
|---|---|---|
| Orchestration | LangGraph `StateGraph`: `intent → retrieval → synthesis → compliance → (critique ↺ synthesis \| narrate \| escalate)`. Runs in a background worker; node completions stream over SSE | — |
| Intent agent | Claude (`LLM_MODEL`, default `claude-opus-5`) with structured output: goal, constraints, retrieval query | Deterministic extractor |
| Hybrid RAG agent | Dense (fastembed `bge-small-en-v1.5` → Qdrant) + BM25 (`rank-bm25`) + knowledge graph (Neo4j, Cypher), fused with Reciprocal Rank Fusion (k=60) and reranked with a cross-encoder (`ms-marco-MiniLM-L-6-v2`) | Embedded Qdrant store; in-process networkx graph |
| Synthesis agent | Claude picks a product + allocation from the pre-screened shortlist; compliance critique is fed back on retries | Deterministic synthesiser |
| Compliance agent | Pydantic rule set + Z3 constraint solving. **Authoritative**: the LLM cannot override a failed rule | — |
| Narrative | Claude writes the client-facing rationale only *after* compliance has decided the status | Template |
| Persistence | SQLAlchemy → PostgreSQL. Audit table protected by `BEFORE UPDATE/DELETE/TRUNCATE` triggers | SQLite with equivalent triggers |
| Auth | JWT bearer tokens (bcrypt passwords); roles `advisor`, `compliance_officer` (read-only) and `admin` | — |
| UI | React + TypeScript + Vite + Tailwind; 11 enterprise sections plus login (not a chatbot) | — |

If Claude errors, times out or returns invalid output, that agent falls back to its deterministic path.
The audit trail records which method was used (`[llm]` / `[deterministic]`).

## Structure

- `backend/`: FastAPI + Pydantic v2 API (`app/graph` for LangGraph, `app/retrieval` for hybrid RAG, `app/compliance`, `app/db` + `app/repositories` for SQLAlchemy, `app/core/security.py` for JWT). Python ≥ 3.12, venv at `backend/.venv`.
- `frontend/`: React UI. `src/lib/api.ts` is the typed API client; `src/lib/auth.tsx` handles session and role gating.
- `docker-compose.yml`: Postgres, Qdrant and Neo4j, plus the containerised backend and frontend under the `app` profile.

## Configuration

Copy `backend/.env.example` to `backend/.env`. Key settings:

- `USE_REAL_LLM=true` + `ANTHROPIC_API_KEY=...` enables the Claude agents. The key is read server-side only;
  it is never returned by any endpoint or bundled into the frontend.
- `DATABASE_URL`: SQLite by default; `postgresql+psycopg://advisory:advisory@localhost:55432/advisory` for Postgres.
- `QDRANT_URL` / `NEO4J_URI` / `NEO4J_PASSWORD`: leave empty for the embedded/in-process fallbacks.
- `JWT_SECRET`: set a long random value. If it's unset, a per-process secret is generated and tokens reset on restart.

## Run

### Option A: local processes (SQLite + embedded retrieval)

```bash
# backend/
./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010
# frontend/
npm install && npx vite --port 5174 --strictPort      # http://localhost:5174
```

If your shell exports `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_API_KEY` (e.g. inside
another tool), prefix the backend command with `env -u ANTHROPIC_BASE_URL -u ANTHROPIC_AUTH_TOKEN -u ANTHROPIC_API_KEY`
so that `backend/.env` is used. On the first start, the embedding and reranker models are downloaded to `backend/data/models`.

### Option B: local backend against real Postgres / Qdrant / Neo4j

```bash
docker-compose up -d       # postgres :55432, qdrant :56333, neo4j :57474/:57687
# backend/
DATABASE_URL=postgresql+psycopg://advisory:advisory@localhost:55432/advisory \
QDRANT_URL=http://localhost:56333 NEO4J_URI=bolt://localhost:57687 NEO4J_PASSWORD=advisory-graph \
  ./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

`GET /api/health` should report `"persistence":"postgresql"`, `"dense":"qdrant-server"` and `"graph":"neo4j"`.

### Option C: fully containerised

```bash
docker-compose --profile app up -d --build   # UI http://localhost:8081, API http://localhost:58010
```

The backend container reads secrets from `backend/.env` at runtime. Nothing secret is baked into either image.

### Demo accounts (DEMO_MODE only)

| Username | Password | Role | Can |
|---|---|---|---|
| `advisor` | `advisor-demo` | Adviser | Everything, including running cases and submitting fact-finds |
| `compliance` | `compliance-demo` | Compliance officer | Read everything; cannot run cases or edit fact-finds (API returns 403) |
| `admin` | `admin-demo` | Administrator | Everything |

The login page lists these accounts only when the backend reports `demo_mode`. Outside demo mode, configure
`BOOTSTRAP_ADMIN_USERNAME` / `BOOTSTRAP_ADMIN_PASSWORD`.

## Verify

- Backend unit and integration tests (offline, LLM faked): `./.venv/Scripts/python.exe -m pytest -q`, `ruff check app tests scripts`, `mypy app`.
- Frontend: `npm run build` (strict TypeScript) and `npm run lint`.
- End-to-end against running servers, with real Claude calls when enabled: `./.venv/Scripts/python.exe scripts/e2e_test.py`.
  It covers auth/roles, every endpoint, all scenarios via live SSE, hybrid retrieval provenance, the LangGraph topology,
  edge cases, CORS, secret leakage and SPA routes. See [TEST_PLAN.md](TEST_PLAN.md).

## Demo scenarios (Advisory Workspace)

| Client | Scenario | Expected outcome |
|---|---|---|
| C-0001 | Clean pass | COMPLIANT after 1 iteration |
| C-0002 | Self-correction | First draft rejected → structured critique → re-synthesis → COMPLIANT (2–3 iterations) |
| C-0004 | Unfixable breach | Concessional cap breach → REQUIRES_HUMAN_REVIEW after 3 iterations |
| C-0006 | Fee/allocation warning | Fee above the 1.75% threshold for an over-55 → WARNING after 1 iteration |

While a case runs, the workspace streams each LangGraph node as it completes. It also shows the compliance
critique fed back to synthesis and the retrieved evidence: which retrievers found each document, its RRF
and rerank scores, and its knowledge-graph paths. Afterwards, inspect the case in **Agent Execution**,
**Compliance** (rule by rule), **Reports** (Statement of Advice, marked DEMO DATA) and **Audit Trail**.
