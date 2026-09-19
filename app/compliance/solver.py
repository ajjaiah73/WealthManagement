from z3 import Real, Solver, Sum, sat
from app.models import AdviceRequest

def verify(req: AdviceRequest, draft: dict):
    findings=[]
    a=draft.get("allocation",{})
    equity=float(a.get("equity_pct",0)); bond=float(a.get("bond_pct",0)); cash=float(a.get("cash_pct",0))
    e,b,c=Real("equity"),Real("bond"),Real("cash")
    s=Solver(); s.add(e==equity,b==bond,c==cash,Sum(e,b,c)==100,e>=0,b>=0,c>=0)
    findings.append({"rule_id":"ALLOC-100","severity":"error","passed":s.check()==sat,"message":"Allocation must be non-negative and total 100%."})
    caps={"conservative":40,"moderate":70,"aggressive":90}
    cap=caps[req.client.risk_tolerance]
    findings.append({"rule_id":"RISK-CAP","severity":"error","passed":equity<=cap,"message":f"Equity allocation must not exceed {cap}% for {req.client.risk_tolerance} risk."})
    fees=[float(p.get("fee_pct",99)) for p in draft.get("recommendations",[])]
    findings.append({"rule_id":"FEE-CAP","severity":"error","passed":all(x<=req.client.max_fee_pct for x in fees),"message":f"Every product fee must be <= {req.client.max_fee_pct}%."})
    blocked=set(req.client.restricted_products)
    used={p.get("product_id") for p in draft.get("recommendations",[])}
    findings.append({"rule_id":"RESTRICTIONS","severity":"error","passed":not bool(blocked & used),"message":"Restricted products must not be recommended."})
    source_ok=all(p.get("source_ids") for p in draft.get("recommendations",[]))
    findings.append({"rule_id":"GROUNDING","severity":"error","passed":source_ok,"message":"Every recommendation must cite retrieved evidence."})
    return findings
