from langgraph.graph import StateGraph, START, END
from app.state import AdvisoryState
from app.retrieval.hybrid import hybrid_search
from app.agents.synthesis import synthesise
from app.compliance.solver import verify
from app.config import settings

def retrieve(state):
    req=state["request"]
    q=f"{req.goal} {req.question} risk {req.client.risk_tolerance} horizon {req.client.investment_horizon_years} years"
    return {"query":q,"contexts":hybrid_search(q),"reflection_count":state.get("reflection_count",0)}
def draft(state):
    return {"draft":synthesise(state["request"],state["contexts"],state.get("critique",""))}
def compliance(state):
    f=verify(state["request"],state["draft"])
    ok=all(x["passed"] for x in f if x["severity"]=="error")
    critique="; ".join(x["message"] for x in f if not x["passed"])
    return {"compliance_findings":f,"compliant":ok,"critique":critique}
def route(state):
    if state["compliant"] or state.get("reflection_count",0)>=settings.max_reflections: return "finalise"
    return "reflect"
def reflect(state):
    return {"reflection_count":state.get("reflection_count",0)+1}
def finalise(state):
    d=state["draft"]
    citations=[{"id":c["id"],"text":c["text"][:500],"metadata":c.get("metadata",{}),"score":c.get("rrf_score",c.get("score"))} for c in state["contexts"]]
    return {"final":{**d,"citations":citations,"compliance_findings":state["compliance_findings"],"compliant":state["compliant"],"reflection_count":state.get("reflection_count",0)}}
b=StateGraph(AdvisoryState)
for n,f in [("retrieve",retrieve),("draft",draft),("compliance",compliance),("reflect",reflect),("finalise",finalise)]: b.add_node(n,f)
b.add_edge(START,"retrieve"); b.add_edge("retrieve","draft"); b.add_edge("draft","compliance")
b.add_conditional_edges("compliance",route,{"reflect":"reflect","finalise":"finalise"}); b.add_edge("reflect","draft"); b.add_edge("finalise",END)
advisory_graph=b.compile()
