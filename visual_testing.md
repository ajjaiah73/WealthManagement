# Visual Testing Guide

A step-by-step manual walkthrough of the UI in a browser. Each step lists what to do and what you
should see. Record results in the checklist at the end. For the automated suites, see [TEST_PLAN.md](TEST_PLAN.md).

## 0. Setup

| Component | URL | Notes |
|---|---|---|
| Frontend | http://localhost:5174 | Vite dev server (`frontend/`: `npx vite --port 5174 --strictPort`) |
| Backend | http://localhost:8010 | `backend/`: `env -u ANTHROPIC_BASE_URL -u ANTHROPIC_AUTH_TOKEN -u ANTHROPIC_API_KEY .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010` |

Before you start:

1. Open http://localhost:8010/api/health. It should show `"llm_enabled":true`, `"orchestrator":"langgraph"`
   and `"retrieval":{"mode":"hybrid","ready":true,...}`.
2. Use a desktop browser at 1280px wide or more. Keep DevTools open on the **Console** and **Network** tabs.
   Note any red console errors on any page.
3. With the LLM enabled, each advisory run takes about **20–90 seconds** (real Claude calls). C-0004 is the
   slowest because it runs three iterations. This is expected.

Demo accounts (shown on the login page in DEMO MODE):

| Username | Password | Role |
|---|---|---|
| `advisor` | `advisor-demo` | Adviser: full access |
| `compliance` | `compliance-demo` | Compliance officer: read-only |
| `admin` | `admin-demo` | Administrator: full access |

---

## 1. Login and session (UI-00)

| # | Action | Expected |
|---|---|---|
| 1.1 | In a fresh tab, open http://localhost:5174/advisory | Redirected to `/login?next=%2Fadvisory`. No app sidebar is visible. |
| 1.2 | Look at the login page | A username/password form and a **demo accounts** card listing the three accounts. |
| 1.3 | Enter `advisor` / `wrong` and submit | An "invalid credentials" style error. You stay on the login page. |
| 1.4 | Enter `nobody` / `x` | The **same** error as 1.3 (no hint about whether the user exists). |
| 1.5 | Click the **advisor** demo card | The username and password fields fill in. |
| 1.6 | Submit | You land on **/advisory** (the `next` target), not the dashboard. |
| 1.7 | Check the top bar | **DEMO MODE** (amber), **Claude claude-opus-5** (green; hover shows the LLM agents), **API Online** (green), and "Demo Advisor / Adviser" with a logout icon. |
| 1.8 | Refresh the page (F5) | You are still logged in, because the session lives in sessionStorage. |
| 1.9 | Open http://localhost:5174/login?next=https://evil.example | After logging in, you stay inside the app (the open redirect is blocked). |
| 1.10 | DevTools → Application → Session Storage | `advisory.token` (a JWT) and `advisory.user` are present. **No** `sk-ant` value anywhere. |

---

## 2. Dashboard (UI-01)

| # | Action | Expected |
|---|---|---|
| 2.1 | Click **Dashboard** in the sidebar | KPI tiles for clients (10), cases run, and pass / warning / human-review counts. |
| 2.2 | Check the recent cases table | Lists cases with colour-coded status badges: green Compliant, amber Warning, purple Requires Human Review. |
| 2.3 | Click a case | Opens that case. |

---

## 3. Clients and Fact Find (UI-02, UI-03)

| # | Action | Expected |
|---|---|---|
| 3.1 | **Clients** → type a surname into search | The table filters live. |
| 3.2 | Click a client row (e.g. C-0001) | Client Detail shows the profile and fact-find completion. |
| 3.3 | Use the CTA to start advice for this client | Advisory Workspace opens with that client preselected. |
| 3.4 | **Fact Find** → choose **C-0003** | Missing fields are highlighted as missing. |

---

## 4. Advisory Workspace: the four core scenarios (UI-04)

Run each from **Advisory Workspace**. Select the client, keep the default request (or type your own), then click
**Run Advisory Case**. For each run, observe the screen while it runs, then again when it finishes.

**While it runs (every scenario):**

- The URL changes immediately to `/advisory/CASE-XXXXXXXX`.
- The status badge shows **In Progress**, with a spinner and "Running — last completed step: …".
- The **Agent Execution Trace** card says *"Streaming LangGraph node completions live."* Steps appear **one by
  one, seconds apart** (not all at once), in the order:
  1. Intent & Parameter Extraction
  2. Hybrid RAG & Market Context
  3. Advisory Synthesis
  4. Neuro-Symbolic Compliance Verification
- The **Retrieved Evidence** card fills in once retrieval has completed.

**When it finishes:** the spinner disappears, the status becomes final, the "View compliance detail →"
and "Generate report →" links appear, and the trace card says *"Recorded audit trail for this case."*

### 4.1 C-0001: clean pass

| Check | Expected |
|---|---|
| Final status | **Compliant** (green) |
| Iterations | **1** |
| Trace | intent → retrieval → synthesis → compliance (success) → narrative written by the LLM |
| Recommendation card | Strategy, product, allocation, fees, rationale (written by Claude), assumptions, risks, disclosures |
| Critique card | **Not shown** |

### 4.2 C-0002: self-correction

| Check | Expected |
|---|---|
| Final status | **Compliant** |
| Iterations | **2** (3 is acceptable if Claude's second choice is also rejected) |
| Trace | The first compliance step is a **failure** (red), then **structured_critique**, then a second Advisory Synthesis and a passing compliance step |
| Critique card | An amber box: *"Compliance critique fed back to synthesis"*, listing the failed rule(s) |
| Recommendation | The final product differs from the first (rejected) draft |

### 4.3 C-0004: unfixable breach → human review

| Check | Expected |
|---|---|
| Final status | **Requires Human Review** (purple) |
| Iterations | **3** |
| Trace | Three synthesis → compliance (failure) cycles, then **max_iterations_reached** |
| Critique card | Shown, referencing the concessional contribution cap (CONTRIB-001: $32,000 > $30,000) |
| Narrative | **No** LLM narrative step: the LLM is never used to explain an escalated case |

### 4.4 C-0006: fee/allocation warning

| Check | Expected |
|---|---|
| Final status | **Warning** (amber) |
| Iterations | **1** |
| Recommendation | Product **P-013**; fee above the 1.75% threshold |

### 4.5 Retrieved Evidence card (on any finished case)

| Check | Expected |
|---|---|
| Header box | Extracted goal, constraints, retrieval query, graph topics |
| Each document | Rank `#1..#n`, title (linking to Documents), doc ID, source |
| Method badges | A mix of **Dense (Qdrant)** (green), **BM25** (amber) and **Knowledge graph** (purple) across the list |
| Scores | `rerank 0.xxx · RRF 0.0xxx` on each row |
| Graph paths | Purple `⑂` lines, e.g. `Client → Topic → Document`, on graph-sourced documents |

### 4.6 Reload a finished case

Refresh `/advisory/CASE-…` on a finished case. You should see the full trace replayed instantly with the final
status. Nothing is stuck at "In Progress".

---

## 5. Role gating (UI-04b)

| # | Action | Expected |
|---|---|---|
| 5.1 | Click the logout icon in the top bar | Back to `/login`. Session storage is cleared. |
| 5.2 | Log in as `compliance` / `compliance-demo` | The top bar shows "Compliance Officer". |
| 5.3 | Go to **Advisory Workspace** | **Run Advisory Case** is disabled, with an amber *"Your role is read-only…"* notice. |
| 5.4 | Open any existing case, Compliance, Audit Trail or Reports | Everything is readable. |
| 5.5 | Log out and log back in as `advisor` for the rest of the guide | — |

---

## 6. Agent Execution (UI-05)

| # | Action | Expected |
|---|---|---|
| 6.1 | **Agent Execution** → select the C-0002 case | A full-page vertical timeline. The critique appears **between** the two synthesis steps. |
| 6.2 | Check each step | Agent label, action badge, success/failure icon, iteration, timestamp. LLM steps show the model. |

## 7. Compliance (UI-06)

| # | Action | Expected |
|---|---|---|
| 7.1 | Open the C-0004 case's compliance view | A rule-by-rule table. **CONTRIB-001** is marked failed (red), with detail and evidence. |
| 7.2 | Open the C-0006 case's compliance view | **FEE-001** and **ALLOC-002** are shown as warnings (amber). There are no failed rules. |
| 7.3 | Check the counts | Passed + failed + warnings equals the number of rules evaluated. |

## 8. Products and Documents (UI-07, UI-08)

| # | Action | Expected |
|---|---|---|
| 8.1 | **Products** → filter by type | The list narrows to that type. |
| 8.2 | Sort by total fee | The order changes correctly. |
| 8.3 | Search for nonsense text | Empty-state message, not a blank area. |
| 8.4 | **Documents** → search "concessional" | Matching docs appear. Clicking one opens the detail panel. |
| 8.5 | From the Retrieved Evidence card, click a document title | Documents opens on that document. |

## 9. Reports (UI-09)

| # | Action | Expected |
|---|---|---|
| 9.1 | On a finished case, click **Generate report →** | A Statement of Advice is rendered with a visible **DEMO DATA** marker, the client name, recommendation and disclosures. |
| 9.2 | Generate for the C-0004 case | The report reflects the human-review status. It does not present the advice as approved. |

## 10. Audit Trail (UI-10)

| # | Action | Expected |
|---|---|---|
| 10.1 | **Audit Trail** | A global event log, newest events included. |
| 10.2 | Filter by agent, then by status | The list narrows correctly. |
| 10.3 | Click a case link | Agent Execution opens for that case. |

## 11. Settings (UI-11)

| # | Action | Expected |
|---|---|---|
| 11.1 | **Settings** → API Status card | Status "ok", DEMO MODE, **LLM Live: Claude claude-opus-5**, and "Signed in as Demo Advisor (Adviser)". |
| 11.2 | Runtime Configuration | Orchestrator *LangGraph StateGraph*, max iterations 3, the compliance engine, LLM agents (`intent_extraction, advisory_synthesis, rationale_narrative`), persistence `sqlite` (or `postgresql`), JWT auth. |
| 11.3 | Hybrid Retrieval card | **Ready** badge, plus: dense `qdrant-embedded` (or `qdrant-server`), embedding `BAAI/bge-small-en-v1.5`, `rank-bm25`, graph `networkx` (or `neo4j`), fusion `rrf(k=60)`, reranker `Xenova/ms-marco-MiniLM-L-6-v2`, 20 indexed chunks. No red error box. |

## 12. Error handling (UI-12, UI-13)

| # | Action | Expected |
|---|---|---|
| 12.1 | Open http://localhost:5174/does-not-exist | A 404 page with "Back to Dashboard". |
| 12.2 | Open http://localhost:5174/advisory/CASE-NOPE | A "case not found" style message, not a crash. |
| 12.3 | DevTools → Application → change `advisory.token` to garbage, then navigate | The next API call returns 401, and you are redirected to `/login?next=…`. |
| 12.4 | Stop the backend, then click through a few pages | Error states and "API Unreachable" in the top bar. No blank white screen. Restart the backend afterwards. |

---

## 13. Optional: real Postgres / Qdrant / Neo4j stack

To repeat sections 4 and 11 against the docker-backed infrastructure:

```bash
docker-compose up -d          # from the repo root
# then start the backend on :8010 with the Option B env vars from README.md
```

Settings should then show persistence `postgresql`, dense `qdrant-server` and graph `neo4j`. Neo4j's browser
is at http://localhost:57474 (user `neo4j`, password `advisory-graph`). Running
`MATCH (n) RETURN labels(n)[0], count(*)` there should list Document 20, Product 13, Topic and ProductType nodes.

For the fully containerised app, run `docker-compose --profile app up -d --build` and use http://localhost:8081.

---

## Results checklist

| ID | Area | Pass / Fail | Notes |
|---|---|---|---|
| UI-00 | Login & session | | |
| UI-01 | Dashboard | | |
| UI-02 | Clients / Client Detail | | |
| UI-03 | Fact Find | | |
| UI-04 | Advisory: C-0001 Compliant, 1 iteration | | |
| UI-04 | Advisory: C-0002 Compliant, 2 iterations + critique | | |
| UI-04 | Advisory: C-0004 Human Review, 3 iterations | | |
| UI-04 | Advisory: C-0006 Warning, 1 iteration | | |
| UI-04 | Live streaming (steps arrive one by one) | | |
| UI-04 | Retrieved Evidence (badges, scores, graph paths) | | |
| UI-04b | Compliance role is read-only | | |
| UI-05 | Agent Execution | | |
| UI-06 | Compliance | | |
| UI-07 | Products | | |
| UI-08 | Documents | | |
| UI-09 | Reports | | |
| UI-10 | Audit Trail | | |
| UI-11 | Settings | | |
| UI-12 | Unknown routes / cases | | |
| UI-13 | Expired token / backend down | | |
| — | No console errors on any page | | |

When reporting a failure, include the page URL, the case ID (from the URL), a screenshot, and any console error text.
