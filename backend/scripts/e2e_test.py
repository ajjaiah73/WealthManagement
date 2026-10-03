"""End-to-end test runner against a *running* backend + frontend.

Exercises authentication and roles, every API the UI depends on, the four
demo scenarios (started in the background and followed live over SSE), hybrid
retrieval evidence, the live LLM agents, report generation, and edge cases
(401/403/404/409/422, CORS, SPA deep links). Test IDs match TEST_PLAN.md at
the repo root. Uses only the standard library.

Usage:
    python scripts/e2e_test.py [--api http://localhost:8010] [--web http://localhost:5174]

Exit code is 0 only if every check passes.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

RESULTS: list[tuple[str, str, bool, str]] = []
AUTH: dict[str, str] = {}  # default Authorization header once logged in


class Response:
    def __init__(self, status: int, body: bytes, headers: dict[str, str]) -> None:
        self.status = status
        self.body = body
        self.headers = {k.lower(): v for k, v in headers.items()}

    def json(self) -> Any:
        return json.loads(self.body)

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


def http(
    method: str,
    url: str,
    payload: Any = None,
    headers: dict[str, str] | None = None,
    timeout: float = 180.0,
) -> Response:
    data = json.dumps(payload).encode() if payload is not None else None
    merged = {**AUTH, **(headers or {})}
    req = urllib.request.Request(url, data=data, method=method, headers={k: v for k, v in merged.items() if v})
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return Response(resp.status, resp.read(), dict(resp.headers))
    except urllib.error.HTTPError as err:
        return Response(err.code, err.read(), dict(err.headers))


def login(api: str, username: str, password: str) -> Response:
    return http("POST", f"{api}/api/auth/login", {"username": username, "password": password},
                headers={"Authorization": ""})


def stream_events(url: str, timeout: float = 600.0) -> list[tuple[float, str, str]]:
    """Reads an SSE stream incrementally; returns (arrival seconds, event name, data)."""
    req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
    out: list[tuple[float, str, str]] = []
    t0 = time.time()
    event = "message"
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        expect(resp.headers.get("content-type", "").startswith("text/event-stream"), "not an SSE response")
        for raw in resp:
            line = raw.decode("utf-8").rstrip("\r\n")
            if line.startswith("event: "):
                event = line[7:]
            elif line.startswith("data: "):
                out.append((time.time() - t0, event, line[6:]))
                event = "message"
    return out


def check(test_id: str, name: str, fn: Callable[[], str | None]) -> None:
    try:
        detail = fn() or ""
        RESULTS.append((test_id, name, True, detail))
    except AssertionError as exc:
        RESULTS.append((test_id, name, False, str(exc)))
    except Exception as exc:  # noqa: BLE001 - report any crash as a failure
        RESULTS.append((test_id, name, False, f"{type(exc).__name__}: {exc}"))
    print(f"{'PASS' if RESULTS[-1][2] else 'FAIL'}  {test_id:7} {name}  {RESULTS[-1][3]}", flush=True)


def expect(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8010")
    parser.add_argument("--web", default="http://localhost:5174")
    args = parser.parse_args()
    api, web = args.api.rstrip("/"), args.web.rstrip("/")
    state: dict[str, Any] = {}

    # ---- 1. Health ---------------------------------------------------------------------
    def health() -> str:
        r = http("GET", f"{api}/api/health")
        expect(r.status == 200, f"status {r.status}")
        body = r.json()
        expect(body["status"] == "ok", f"body {body}")
        expect(body["demo_mode"] is True, "demo_mode should be true")
        expect(body["orchestrator"] == "langgraph", f"orchestrator {body['orchestrator']}")
        expect(body["auth_enabled"] is True, "auth should be enabled")
        expect(body["max_iterations"] == 3, "max_iterations should be 3")
        state["llm"] = body["llm_enabled"]
        state["retrieval"] = body["retrieval"]
        return (f"llm={body['llm_model'] if body['llm_enabled'] else 'off'} "
                f"persistence={body['persistence']} retrieval={body['retrieval']['mode']}")

    check("API-01", "Health endpoint", health)

    def hybrid_retrieval_ready() -> str:
        r = state["retrieval"]
        expect(r["mode"] == "hybrid", f"retrieval mode {r['mode']}")
        expect(r["ready"] is True and r["errors"] == {}, f"retrieval not healthy: {r}")
        expect(all(r.get(k) for k in ("dense", "bm25", "graph", "reranker", "fusion")), f"missing component: {r}")
        return f"dense={r['dense']} graph={r['graph']} reranker={r['reranker']} chunks={r['chunks']}"

    check("RET-00", "Hybrid retrieval components ready", hybrid_retrieval_ready)

    # ---- 2. Authentication & roles -----------------------------------------------------
    def unauthenticated() -> str:
        for path in ("/api/clients", "/api/advisory", "/api/audit"):
            r = http("GET", f"{api}{path}")
            expect(r.status == 401, f"{path} without token -> {r.status}")
        r = http("GET", f"{api}/api/clients", headers={"Authorization": "Bearer forged.token.value"})
        expect(r.status == 401, f"forged token -> {r.status}")
        return "401 without token and with a forged token"

    def bad_password() -> str:
        a = login(api, "advisor", "wrong-password")
        b = login(api, "no-such-user", "x")
        expect(a.status == 401 and b.status == 401, f"{a.status}/{b.status}")
        expect(a.json() == b.json(), "login errors must not reveal whether the user exists")
        return "401, identical error for unknown user"

    def advisor_login() -> str:
        r = login(api, "advisor", "advisor-demo")
        expect(r.status == 200, f"status {r.status}: {r.text[:200]}")
        body = r.json()
        expect(body["user"]["role"] == "advisor", f"role {body['user']}")
        AUTH["Authorization"] = f"Bearer {body['access_token']}"
        state["token"] = body["access_token"]
        me = http("GET", f"{api}/api/auth/me").json()
        expect(me["user_id"] == "advisor", f"me {me}")
        return f"token issued, expires {body['expires_at']}"

    def compliance_read_only() -> str:
        r = login(api, "compliance", "compliance-demo")
        expect(r.status == 200, f"login {r.status}")
        hdr = {"Authorization": f"Bearer {r.json()['access_token']}"}
        expect(http("GET", f"{api}/api/clients", headers=hdr).status == 200, "compliance cannot read")
        for path, payload in (("/api/advisory/run", {"client_id": "C-0001"}),
                              ("/api/advisory/start", {"client_id": "C-0001"}),
                              ("/api/fact-find", {"client_id": "C-0010", "updates": {}})):
            w = http("POST", f"{api}{path}", payload, headers=hdr)
            expect(w.status == 403, f"compliance POST {path} -> {w.status}")
        return "reads 200, advisory/fact-find writes 403"

    check("AUTH-01", "Protected API rejects missing/forged token", unauthenticated)
    check("AUTH-02", "Bad credentials rejected", bad_password)
    check("AUTH-03", "Advisor login + /me", advisor_login)
    check("AUTH-04", "Compliance officer is read-only", compliance_read_only)

    # ---- 3. Reference data -------------------------------------------------------------
    def list_count(path: str, n: int, key: str) -> Callable[[], str]:
        def run() -> str:
            r = http("GET", f"{api}{path}")
            expect(r.status == 200, f"status {r.status}")
            items = r.json()
            expect(len(items) == n, f"expected {n} items, got {len(items)}")
            ids = [i[key] for i in items]
            expect(len(set(ids)) == n, "duplicate ids")
            state[path] = items
            return f"{n} items"

        return run

    check("API-02", "List clients (10)", list_count("/api/clients", 10, "client_id"))
    check("API-03", "List products (13)", list_count("/api/products", 13, "product_id"))
    check("API-04", "List documents (20)", list_count("/api/documents", 20, "document_id"))

    def each_client_and_fact_find() -> str:
        missing_total = 0
        for c in state.get("/api/clients", []):
            cid = c["client_id"]
            r = http("GET", f"{api}/api/clients/{cid}")
            expect(r.status == 200 and r.json()["client_id"] == cid, f"client {cid}")
            ff = http("GET", f"{api}/api/fact-find/{cid}")
            expect(ff.status == 200, f"fact-find {cid} status {ff.status}")
            fields = ff.json()["fields"]
            expect(all(f["status"] in ("present", "missing") for f in fields), "bad field status")
            missing_total += sum(f["status"] == "missing" for f in fields)
        return f"10 profiles + fact-finds OK, {missing_total} missing fields flagged"

    check("API-05", "Client detail + fact-find for every client", each_client_and_fact_find)

    def each_document() -> str:
        for d in state.get("/api/documents", []):
            r = http("GET", f"{api}/api/documents/{d['document_id']}")
            expect(r.status == 200, f"document {d['document_id']} status {r.status}")
        return "20 document details OK"

    check("API-06", "Document detail for every document", each_document)

    def product_fees_sane() -> str:
        for p in state.get("/api/products", []):
            total = p["management_fee_pct"] + p["administration_fee_pct"]
            expect(0 < total < 5, f"{p['product_id']} total fee {total}")
        return "all fees within (0, 5)%"

    check("API-07", "Product fee data sane", product_fees_sane)

    # ---- 4. Demo scenarios (background start + live SSE) -------------------------------
    # Iteration counts are ranges: when the LLM synthesis agent is live, its corrected
    # draft may need one more critique round, but the outcome class is fixed by the
    # symbolic rules (the LLM cannot override a failed rule).
    scenarios = [
        ("SCN-01", "C-0001", {"COMPLIANT"}, (1, 1), "Clean pass"),
        ("SCN-02", "C-0002", {"COMPLIANT"}, (2, 3), "Self-correction"),
        ("SCN-03", "C-0004", {"REQUIRES_HUMAN_REVIEW"}, (3, 3), "Unfixable breach escalation"),
        ("SCN-04", "C-0006", {"WARNING"}, (1, 1), "Fee/allocation warning"),
    ]

    for test_id, client_id, want_status, want_iter, label in scenarios:

        def run_scenario(client_id: str = client_id, want_status: set[str] = want_status,
                         want_iter: tuple[int, int] = want_iter) -> str:
            t0 = time.time()
            r = http("POST", f"{api}/api/advisory/start", {"client_id": client_id})
            expect(r.status == 202, f"status {r.status}: {r.text[:200]}")
            started = r.json()
            expect(started["status"] == "IN_PROGRESS", f"start status {started['status']}")
            # EventSource cannot send headers, so the stream authenticates via ?access_token=
            events = stream_events(f"{api}/api/advisory/{started['case_id']}/stream"
                                   f"?access_token={state['token']}")
            elapsed = time.time() - t0
            expect(bool(events) and events[-1][1] == "done", "stream did not end with a done event")
            case = json.loads(events[-1][2])
            state[client_id] = case
            state[client_id + ":stream"] = events
            expect(case["status"] in want_status, f"status {case['status']} not in {want_status}")
            lo, hi = want_iter
            expect(lo <= case["iteration_count"] <= hi,
                   f"iterations {case['iteration_count']} not in {want_iter}")
            expect(case["recommendation"] is not None, "no recommendation")
            expect(case["recommendation"]["rationale"].strip() != "", "empty rationale")
            steps = [e for e in events if e[1] == "message"]
            return (f"{case['case_id']} {case['status']} iter={case['iteration_count']} "
                    f"product={case['recommendation']['product_id']} {len(steps)} live events ({elapsed:.1f}s)")

        check(test_id, f"{label}: {client_id}", run_scenario)

    def live_streaming() -> str:
        events = state["C-0002:stream"]
        first, done = events[0][0], events[-1][0]
        actions = [json.loads(d)["action"] for _, e, d in events if e == "message"]
        expect(actions[:3] == ["extract_intent", "hybrid_retrieval", "synthesize_strategy"],
               f"unexpected node order {actions[:3]}")
        expect("structured_critique" in actions, "critique step not streamed")
        if state.get("llm"):
            # With live model calls the steps genuinely arrive over time, not as one burst.
            expect(done - first > 1.0, f"events not incremental: first {first:.2f}s, done {done:.2f}s")
        return f"first event at {first:.1f}s, done at {done:.1f}s, {len(actions)} steps"

    check("SSE-02", "Agent steps stream live while the graph runs", live_streaming)

    def retrieval_evidence() -> str:
        out = []
        seen_sources: set[str] = set()
        for cid in ("C-0001", "C-0002", "C-0004"):
            r = http("GET", f"{api}/api/advisory/{state[cid]['case_id']}/retrieval")
            expect(r.status == 200, f"{cid} status {r.status}")
            docs = r.json()
            expect(len(docs) > 0, f"{cid} no evidence")
            expect([d["rank"] for d in docs] == list(range(1, len(docs) + 1)), f"{cid} ranks not 1..n")
            for d in docs:
                method = d["retrieval_method"]
                expect(method == "fused", f"{cid} {d['document_id']} method {method}")
                expect(d["fusion_score"] is not None and 0 <= d["rerank_score"] <= 1, f"{cid} bad scores")
                seen_sources.update(d["retrieval_sources"])
            out.append(f"{cid}:{','.join(d['document_id'] for d in docs[:3])}")
        expect({"dense", "bm25", "graph"} <= seen_sources, f"sources seen {seen_sources}")
        detail = http("GET", f"{api}/api/advisory/{state['C-0002']['case_id']}/detail").json()
        expect(bool(detail["graph_context"]), "no knowledge-graph context recorded")
        expect(bool(detail["retrieval_query"]), "no retrieval query recorded")
        return "; ".join(out) + f" | sources={sorted(seen_sources)}"

    check("RET-01", "Hybrid retrieval evidence (dense+BM25+graph, RRF, rerank)", retrieval_evidence)

    def pipeline_graph() -> str:
        r = http("GET", f"{api}/api/advisory/graph")
        expect(r.status == 200, f"status {r.status}")
        mermaid = r.json()["mermaid"]
        for node in ("intent", "retrieval", "synthesis", "compliance", "critique", "escalate", "narrate"):
            expect(node in mermaid, f"node {node} missing from compiled graph")
        return "compiled LangGraph StateGraph with critique loop"

    check("ORC-01", "LangGraph topology", pipeline_graph)

    def case_roundtrip() -> str:
        for cid in ("C-0001", "C-0002", "C-0004", "C-0006"):
            case = state[cid]
            r = http("GET", f"{api}/api/advisory/{case['case_id']}")
            expect(r.status == 200 and r.json() == case, f"{cid} GET mismatch")
        listed = {c["case_id"] for c in http("GET", f"{api}/api/advisory").json()}
        expect(all(state[c]["case_id"] in listed for c in ("C-0001", "C-0004")), "case not listed")
        return f"{len(listed)} cases listed"

    check("SCN-05", "Case GET + list round-trip", case_roundtrip)

    def compliance_checks() -> str:
        out = []
        for cid, want, must_fail in (
            ("C-0001", "COMPLIANT", None),
            ("C-0002", "COMPLIANT", None),
            ("C-0004", "REJECTED", "CONTRIB-001"),
            ("C-0006", "WARNING", "FEE-001"),
        ):
            r = http("GET", f"{api}/api/compliance/{state[cid]['case_id']}")
            expect(r.status == 200, f"{cid} status {r.status}")
            c = r.json()
            expect(c["status"] == want, f"{cid} compliance {c['status']} != {want}")
            expect(c["rules_evaluated"] == len(c["rule_results"]), f"{cid} count mismatch")
            expect(c["rules_passed"] + c["rules_failed"] + c["warnings"] == c["rules_evaluated"],
                   f"{cid} passed+failed+warnings != evaluated")
            if must_fail:
                rule = next((x for x in c["rule_results"] if x["rule_id"] == must_fail), None)
                expect(rule is not None and not rule["passed"], f"{cid} {must_fail} should fail")
            else:
                expect(c["rules_failed"] == 0, f"{cid} has failed rules")
            expect(len(c["mandatory_disclosures"]) > 0, f"{cid} no disclosures")
            out.append(f"{cid}={c['status']}")
        return ", ".join(out)

    check("CMP-01", "Compliance results per scenario", compliance_checks)

    def audit_trail() -> str:
        r = http("GET", f"{api}/api/audit/{state['C-0002']['case_id']}")
        events = r.json()
        expect(r.status == 200 and len(events) > 0, "no audit events")
        actions = [e["action"] for e in events]
        expect("structured_critique" in actions, f"no critique in {actions}")
        want = state["C-0002"]["iteration_count"]
        expect(max(e["iteration"] for e in events) == want, f"C-0002 should reach iteration {want}")
        ts = [e["timestamp"] for e in events]
        expect(ts == sorted(ts), "audit events not chronological")
        all_events = http("GET", f"{api}/api/audit").json()
        expect(len(all_events) >= len(events), "global audit smaller than case audit")
        return f"{len(events)} events for C-0002, {len(all_events)} global"

    check("AUD-01", "Audit trail with self-correction critique", audit_trail)

    def llm_narrative() -> str:
        if not state.get("llm"):
            return "SKIPPED: LLM disabled (template fallback in use)"
        events = http("GET", f"{api}/api/audit/{state['C-0001']['case_id']}").json()
        llm = [e for e in events if e["action"] == "llm_narrative"]
        expect(len(llm) == 1, "expected one llm_narrative audit event")
        expect(llm[0]["model"] is not None, "llm event missing model")
        hr = http("GET", f"{api}/api/audit/{state['C-0004']['case_id']}").json()
        expect(not any(e["action"] == "llm_narrative" for e in hr),
               "LLM must not run for REQUIRES_HUMAN_REVIEW")
        return f"rationale written by {llm[0]['model']}; skipped for human-review case"

    check("LLM-01", "Live LLM rationale + human-review skip", llm_narrative)

    def llm_agents() -> str:
        if not state.get("llm"):
            return "SKIPPED: LLM disabled (deterministic agents in use)"
        out = []
        for cid in ("C-0001", "C-0002", "C-0004"):
            events = http("GET", f"{api}/api/audit/{state[cid]['case_id']}").json()
            intent = next(e for e in events if e["action"] == "extract_intent")
            by_llm = intent["details"].startswith("[llm]") and bool(intent["model"])
            expect(by_llm, f"{cid} intent not by LLM")
            synth = [e for e in events if e["action"] == "synthesize_strategy"]
            methods = [e["details"].split("]")[0].strip("[") for e in synth]
            out.append(f"{cid} synthesis={'/'.join(methods)}")
        # C-0004 runs three LLM drafts and is still escalated: the model cannot talk its
        # way past the failed contribution-cap rule.
        expect(state["C-0004"]["status"] == "REQUIRES_HUMAN_REVIEW", "LLM overrode a failed rule")
        return "; ".join(out)

    check("LLM-02", "Intent + synthesis agents on Claude; cannot override rules", llm_agents)

    def sse_replay() -> str:
        case_id = state["C-0002"]["case_id"]
        r = http("GET", f"{api}/api/advisory/{case_id}/stream", headers={"Accept": "text/event-stream"})
        expect(r.status == 200, f"status {r.status}")
        expect(r.headers.get("content-type", "").startswith("text/event-stream"),
               f"content-type {r.headers.get('content-type')}")
        data_lines = [ln for ln in r.text.splitlines() if ln.startswith("data: ")]
        expect("event: done" in r.text, "no done event")
        audit_len = len(http("GET", f"{api}/api/audit/{case_id}").json())
        expect(len(data_lines) - 1 == audit_len, f"stream {len(data_lines) - 1} events != audit {audit_len}")
        json.loads(data_lines[0][6:])
        return f"{audit_len} events + done"

    check("SSE-01", "SSE stream replays a completed case's audit trail", sse_replay)

    def reports() -> str:
        out = []
        for cid in ("C-0001", "C-0002", "C-0004", "C-0006"):
            r = http("POST", f"{api}/api/reports/{state[cid]['case_id']}/generate")
            expect(r.status == 200, f"{cid} status {r.status}: {r.text[:200]}")
            soa = r.json()
            expect(soa["is_demo_data"] is True, f"{cid} not flagged demo")
            expect(soa["client_id"] == cid, f"{cid} client mismatch")
            expect(soa["executive_summary"].strip() != "", f"{cid} empty summary")
            out.append(f"{cid}={soa['compliance_verification']['status']}")
        return ", ".join(out)

    check("RPT-01", "Statement of Advice for every scenario", reports)

    def all_clients_no_5xx() -> str:
        statuses: dict[str, str] = {}
        for c in state.get("/api/clients", []):
            cid = c["client_id"]
            if cid in state:
                statuses[cid] = state[cid]["status"]
                continue
            r = http("POST", f"{api}/api/advisory/run", {"client_id": cid})
            expect(r.status == 201, f"{cid} status {r.status}: {r.text[:200]}")
            statuses[cid] = r.json()["status"]
        expect("IN_PROGRESS" not in statuses.values(), "a synchronous run returned a non-terminal case")
        return ", ".join(f"{k}={v}" for k, v in sorted(statuses.items()))

    check("SCN-06", "Advisory runs for all 10 clients without errors", all_clients_no_5xx)

    # ---- 5. Edge cases -----------------------------------------------------------------
    edge: list[tuple[str, str, str, str, Any, int]] = [
        ("EDG-01", "Unknown client detail", "GET", "/api/clients/C-9999", None, 404),
        ("EDG-02", "Unknown client fact-find", "GET", "/api/fact-find/C-9999", None, 404),
        ("EDG-03", "Advisory run for unknown client", "POST", "/api/advisory/run",
         {"client_id": "C-9999"}, 404),
        ("EDG-04", "Advisory run missing client_id", "POST", "/api/advisory/run", {}, 422),
        ("EDG-04b", "Background start for unknown client", "POST", "/api/advisory/start",
         {"client_id": "C-9999"}, 404),
        ("EDG-05", "Unknown advisory case", "GET", "/api/advisory/CASE-NOPE", None, 404),
        ("EDG-06", "Stream for unknown case", "GET", "/api/advisory/CASE-NOPE/stream", None, 404),
        ("EDG-07", "Compliance for unknown case", "GET", "/api/compliance/CASE-NOPE", None, 404),
        ("EDG-08", "Report for unknown case", "POST", "/api/reports/CASE-NOPE/generate", None, 404),
        ("EDG-09", "Unknown document", "GET", "/api/documents/DOC-NOPE", None, 404),
        ("EDG-10", "Fact-find update for unknown client", "POST", "/api/fact-find",
         {"client_id": "C-9999", "updates": {"age": 40}}, 404),
        ("EDG-11", "Fact-find update with invalid type", "POST", "/api/fact-find",
         {"client_id": "C-0010", "updates": {"age": "not-a-number"}}, 422),
        ("EDG-12", "Fact-find update with unknown field", "POST", "/api/fact-find",
         {"client_id": "C-0010", "updates": {"hacker_field": 1}}, 422),
        ("EDG-13", "Fact-find update cannot change client_id", "POST", "/api/fact-find",
         {"client_id": "C-0010", "updates": {"client_id": "C-0001"}}, 422),
        ("EDG-14", "Duplicate client create", "POST", "/api/clients",
         None, 409),
        ("EDG-15", "Unknown API route", "GET", "/api/does-not-exist", None, 404),
        ("EDG-16", "Wrong method on list endpoint", "DELETE", "/api/clients", None, 405),
    ]

    for test_id, name, method, path, payload, want in edge:

        def run_edge(method: str = method, path: str = path, payload: Any = payload,
                     want: int = want, test_id: str = test_id) -> str:
            if test_id == "EDG-14":
                payload = http("GET", f"{api}/api/clients/C-0001").json()
            r = http(method, f"{api}{path}", payload)
            expect(r.status == want, f"expected {want}, got {r.status}: {r.text[:200]}")
            return f"{r.status}"

        check(test_id, name, run_edge)

    def audit_unknown_case() -> str:
        r = http("GET", f"{api}/api/audit/CASE-NOPE")
        expect(r.status == 200 and r.json() == [], f"{r.status} {r.text[:100]}")
        return "200 []"

    check("EDG-17", "Audit trail for unknown case is empty", audit_unknown_case)

    def fact_find_valid_update() -> str:
        before = http("GET", f"{api}/api/clients/C-0010").json()
        r = http("POST", f"{api}/api/fact-find",
                 {"client_id": "C-0010", "updates": {"target_retirement_age": 66}})
        expect(r.status == 200, f"status {r.status}: {r.text[:200]}")
        after = http("GET", f"{api}/api/clients/C-0010").json()
        expect(after["target_retirement_age"] == 66, "update not persisted")
        expect(after["client_id"] == "C-0010", "client_id changed")
        http("POST", f"{api}/api/fact-find",
             {"client_id": "C-0010",
              "updates": {"target_retirement_age": before["target_retirement_age"]}})
        return "valid update persisted and reverted"

    check("EDG-18", "Fact-find valid update persists", fact_find_valid_update)

    def edge_client_state_intact() -> str:
        c = http("GET", f"{api}/api/clients/C-0010").json()
        expect(isinstance(c["age"], int | None), f"age corrupted: {c['age']!r}")
        expect("hacker_field" not in c, "unknown field leaked into profile")
        return "C-0010 not corrupted by rejected updates"

    check("EDG-19", "Rejected updates leave profile intact", edge_client_state_intact)

    # ---- 6. CORS, secrets & frontend ---------------------------------------------------
    def cors(origin: str, allowed: bool) -> Callable[[], str]:
        def run() -> str:
            r = http("OPTIONS", f"{api}/api/clients", headers={
                "Origin": origin, "Access-Control-Request-Method": "GET"})
            got = r.headers.get("access-control-allow-origin")
            if allowed:
                expect(r.status == 200 and got == origin, f"{r.status} allow-origin={got}")
            else:
                expect(got != origin, f"origin {origin} unexpectedly allowed")
            return f"{r.status} allow-origin={got}"

        return run

    check("SEC-01", "CORS allows frontend origin", cors("http://localhost:5174", True))
    check("SEC-02", "CORS rejects foreign origin", cors("http://evil.example.com", False))

    def secret_not_exposed() -> str:
        body = "".join(http("GET", f"{api}{p}").text for p in (
            "/api/health", "/openapi.json", "/api/auth/me", "/api/audit", "/api/advisory"))
        body += login(api, "advisor", "advisor-demo").text
        expect("sk-ant" not in body, "API key leaked in API responses")
        env = http("GET", f"{web}/.env")
        expect("sk-ant" not in env.text, "API key served by frontend dev server")
        return "no key material in health/openapi/auth/audit/frontend"

    check("SEC-03", "API key never exposed", secret_not_exposed)

    routes = ["/", "/login", "/clients", "/clients/C-0001", "/fact-find", "/advisory",
              f"/advisory/{state.get('C-0001', {}).get('case_id', 'x')}", "/agent-execution",
              "/compliance", "/products", "/documents", "/reports", "/audit-trail",
              "/settings", "/this-route-does-not-exist"]

    def spa_routes() -> str:
        for route in routes:
            r = http("GET", f"{web}{route}", headers={"Accept": "text/html"})
            expect(r.status == 200, f"{route} -> {r.status}")
            expect('<div id="root">' in r.text, f"{route} missing root div")
        return f"{len(routes)} deep links serve the SPA shell"

    check("WEB-01", "Frontend deep links (incl. unknown route)", spa_routes)

    def frontend_bundle() -> str:
        r = http("GET", f"{web}/src/main.tsx")
        expect(r.status == 200, f"main.tsx -> {r.status}")
        app = http("GET", f"{web}/src/App.tsx")
        expect(app.status == 200, f"App.tsx -> {app.status}")
        for page in ("Dashboard", "Clients", "FactFind", "Advisory", "AgentExecution",
                     "Compliance", "Products", "Documents", "Reports", "AuditTrail", "Settings"):
            expect(page in app.text, f"route component {page} not wired")
        expect("Login" in app.text and "RequireAuth" in app.text, "login route / auth guard not wired")
        expect('path: "*"' in app.text or 'path="*"' in app.text, "no catch-all 404 route")
        return "all 11 section components + login guard wired + 404 route"

    check("WEB-02", "Frontend modules compile and all sections wired", frontend_bundle)

    # ---- Report ------------------------------------------------------------------------
    failed = [r for r in RESULTS if not r[2]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    for test_id, name, _, detail in failed:
        print(f"  FAILED {test_id} {name}: {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
