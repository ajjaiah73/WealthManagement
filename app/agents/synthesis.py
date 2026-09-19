import json
from openai import OpenAI
from app.config import settings

# def _fallback(req, contexts, critique=""):
#     risk=req.client.risk_tolerance
#     alloc={"conservative":(35,50,15),"moderate":(60,30,10),"aggressive":(80,15,5)}[risk]
#     usable=contexts[:3] or [{"id":"sample-rule","text":"Diversify across asset classes and keep fees within the client's limit.","metadata":{}}]
#     cats=[("EQUITY-IDX","Diversified Equity Index","equity",alloc[0]),("BOND-IDX","Investment Grade Bond Fund","bond",alloc[1]),("CASH-MMF","Cash or Money Market","cash",alloc[2])]
#     recs=[]
#     for i,(pid,name,cat,pct) in enumerate(cats):
#         if pct:
#             src=str(usable[i%len(usable)]["id"])
#             recs.append({"product_id":pid,"name":name,"category":cat,"allocation_pct":pct,"fee_pct":0.5,"rationale":f"Supports the {risk} profile and {req.client.investment_horizon_years}-year horizon.","source_ids":[src]})
#     return {"statement_of_advice":f"For the stated goal, consider a diversified {risk} allocation. This educational prototype uses retrieved policy and product context and requires professional review before action.","allocation":{"equity_pct":alloc[0],"bond_pct":alloc[1],"cash_pct":alloc[2]},"recommendations":recs,"audit_notes":["Pydantic input validation completed.","Hybrid evidence supplied to synthesis."] + ([f"Reflection applied: {critique}"] if critique else [])}

# def _fallback(req, contexts, critique=""):
#     """
#     Deterministic fallback used when the synthesis agent cannot produce a
#     grounded recommendation. Builds a superannuation/retirement-pension
#     advisory summary from the client's risk tolerance and life stage,
#     mapped to CFS-style product categories (accumulation, transition to
#     retirement, account-based pension) rather than generic asset classes.
#     """
#     risk = req.client.risk_tolerance
#     stage = getattr(req.client, "life_stage", "working")  # working | transition_to_retirement | retired
#     horizon = req.client.investment_horizon_years

#     # Growth / defensive split by risk profile (superannuation convention,
#     # not equity/bond/cash — growth assets = shares & property, defensive = bonds & cash)
#     growth_pct, defensive_pct = {
#         "conservative": (30, 70),
#         "moderate": (70, 30),
#         "aggressive": (90, 10),
#     }[risk]

#     usable = contexts[:3] or [
#         {"id": "sample-rule", "text": "Diversify across growth and defensive assets and keep fees within the client's limit.", "metadata": {}}
#     ]

#     # Product categories vary by life stage: accumulation, TTR, or retirement-phase pension
#     if stage == "retired":
#         cats = [
#             ("PEN-ABP-GRW", "FirstChoice Wholesale Pension \u2014 Growth", "pension-growth", round(growth_pct * 0.55)),
#             ("PEN-ABP-BAL", "FirstChoice Wholesale Pension \u2014 Balanced", "pension-growth", round(growth_pct * 0.45)),
#             ("PEN-ABP-CON", "FirstChoice Wholesale Pension \u2014 Conservative", "pension-defensive", defensive_pct),
#         ]
#         fee_pct = 0.55
#     elif stage == "transition_to_retirement":
#         cats = [
#             ("TTR-BAL", "FirstChoice Wholesale Pension TTR \u2014 Balanced", "ttr-growth", round(growth_pct * 0.7)),
#             ("TTR-GRW", "FirstChoice Wholesale Pension TTR \u2014 Growth", "ttr-growth", round(growth_pct * 0.3)),
#             ("TTR-CON", "FirstChoice Wholesale Pension TTR \u2014 Conservative", "ttr-defensive", defensive_pct),
#         ]
#         fee_pct = 0.55
#     else:  # working / accumulation phase
#         cats = [
#             ("MYS-LIFESTAGE", "MySuper Lifestage (default accumulation)", "super-growth", round(growth_pct * 0.5)),
#             ("WSP-CHOICE", "FirstChoice Wholesale Personal Super \u2014 Choice option", "super-growth", round(growth_pct * 0.5)),
#             ("WSP-DEFENSIVE", "FirstChoice Wholesale Personal Super \u2014 Defensive/Cash", "super-defensive", defensive_pct),
#         ]
#         fee_pct = 0.65

#     recs = []
#     for i, (pid, name, cat, pct) in enumerate(cats):
#         if pct:
#             src = str(usable[i % len(usable)]["id"])
#             recs.append({
#                 "product_id": pid,
#                 "name": name,
#                 "category": cat,
#                 "allocation_pct": pct,
#                 "fee_pct": fee_pct,
#                 "rationale": (
#                     f"Aligned to a {risk} risk profile, {stage.replace('_', ' ')} life stage, "
#                     f"and {horizon}-year investment horizon."
#                 ),
#                 "source_ids": [src],
#             })

#     stage_label = stage.replace("_", " ")
#     statement_of_advice = (
#         f"For a member in the {stage_label} phase with a {risk} risk tolerance and a {horizon}-year horizon, "
#         f"consider a {growth_pct}% growth / {defensive_pct}% defensive superannuation allocation across the "
#         f"recommended CFS product categories below. This educational prototype uses retrieved policy and "
#         f"product context and requires professional review before action."
#     )

#     audit_notes = [
#         "Pydantic input validation completed.",
#         "Hybrid evidence supplied to synthesis.",
#         f"Allocation derived from {risk} risk profile and {stage_label} life stage rules.",
#     ]
#     if stage in ("transition_to_retirement", "retired"):
#         audit_notes.append("Preservation age / condition-of-release check recommended before finalising advice.")
#     if critique:
#         audit_notes.append(f"Reflection applied: {critique}")

#     return {
#         "statement_of_advice": statement_of_advice,
#         "allocation": {"growth_pct": growth_pct, "defensive_pct": defensive_pct},
#         "recommendations": recs,
#         "audit_notes": audit_notes,
#     }

def _fallback(req, contexts, critique=""):
    """
    Deterministic fallback used when the synthesis agent cannot produce a
    grounded recommendation. Builds a superannuation/retirement-pension
    advisory summary from the client's risk tolerance and life stage,
    mapped to CFS-style product categories (accumulation, transition to
    retirement, account-based pension).

    NOTE: `allocation` keeps the equity_pct/bond_pct/cash_pct field names
    required by the existing FastAPI response model. In a superannuation
    context, equity_pct represents growth assets (shares/property) and
    bond_pct + cash_pct together represent defensive assets.
    """
    risk = req.client.risk_tolerance
    stage = getattr(req.client, "life_stage", "working")  # working | transition_to_retirement | retired
    horizon = req.client.investment_horizon_years

    # equity_pct = growth assets, bond_pct + cash_pct = defensive assets
    equity_pct, bond_pct, cash_pct = {
        "conservative": (30, 50, 20),
        "moderate": (70, 20, 10),
        "aggressive": (90, 8, 2),
    }[risk]
    growth_pct = equity_pct
    defensive_pct = bond_pct + cash_pct

    usable = contexts[:3] or [
        {"id": "sample-rule", "text": "Diversify across growth and defensive assets and keep fees within the client's limit.", "metadata": {}}
    ]

    # Product categories vary by life stage: accumulation, TTR, or retirement-phase pension
    if stage == "retired":
        cats = [
            ("PEN-ABP-GRW", "FirstChoice Wholesale Pension \u2014 Growth", "pension-growth", round(growth_pct * 0.55)),
            ("PEN-ABP-BAL", "FirstChoice Wholesale Pension \u2014 Balanced", "pension-growth", round(growth_pct * 0.45)),
            ("PEN-ABP-CON", "FirstChoice Wholesale Pension \u2014 Conservative", "pension-defensive", defensive_pct),
        ]
        fee_pct = 0.55
    elif stage == "transition_to_retirement":
        cats = [
            ("TTR-BAL", "FirstChoice Wholesale Pension TTR \u2014 Balanced", "ttr-growth", round(growth_pct * 0.7)),
            ("TTR-GRW", "FirstChoice Wholesale Pension TTR \u2014 Growth", "ttr-growth", round(growth_pct * 0.3)),
            ("TTR-CON", "FirstChoice Wholesale Pension TTR \u2014 Conservative", "ttr-defensive", defensive_pct),
        ]
        fee_pct = 0.55
    else:  # working / accumulation phase
        cats = [
            ("MYS-LIFESTAGE", "MySuper Lifestage (default accumulation)", "super-growth", round(growth_pct * 0.5)),
            ("WSP-CHOICE", "FirstChoice Wholesale Personal Super \u2014 Choice option", "super-growth", round(growth_pct * 0.5)),
            ("WSP-DEFENSIVE", "FirstChoice Wholesale Personal Super \u2014 Defensive/Cash", "super-defensive", defensive_pct),
        ]
        fee_pct = 0.65

    recs = []
    for i, (pid, name, cat, pct) in enumerate(cats):
        if pct:
            src = str(usable[i % len(usable)]["id"])
            recs.append({
                "product_id": pid,
                "name": name,
                "category": cat,
                "allocation_pct": pct,
                "fee_pct": fee_pct,
                "rationale": (
                    f"Aligned to a {risk} risk profile, {stage.replace('_', ' ')} life stage, "
                    f"and {horizon}-year investment horizon."
                ),
                "source_ids": [src],
            })

    stage_label = stage.replace("_", " ")
    statement_of_advice = (
        f"For a member in the {stage_label} phase with a {risk} risk tolerance and a {horizon}-year horizon, "
        f"consider a {growth_pct}% growth / {defensive_pct}% defensive superannuation allocation across the "
        f"recommended CFS product categories below. This educational prototype uses retrieved policy and "
        f"product context and requires professional review before action."
    )

    audit_notes = [
        "Pydantic input validation completed.",
        "Hybrid evidence supplied to synthesis.",
        f"Allocation derived from {risk} risk profile and {stage_label} life stage rules.",
    ]
    if stage in ("transition_to_retirement", "retired"):
        audit_notes.append("Preservation age / condition-of-release check recommended before finalising advice.")
    if critique:
        audit_notes.append(f"Reflection applied: {critique}")

    return {
        "statement_of_advice": statement_of_advice,
        "allocation": {"equity_pct": equity_pct, "bond_pct": bond_pct, "cash_pct": cash_pct},
        "recommendations": recs,
        "audit_notes": audit_notes,
    }

def synthesise(req, contexts, critique=""):
    if settings.mock_llm or not settings.openai_api_key:
        return _fallback(req,contexts,critique)
    client=OpenAI(api_key=settings.openai_api_key,base_url=settings.openai_base_url)
    schema='Return JSON only with statement_of_advice, allocation, recommendations, and audit_notes. Allocation totals 100. Every recommendation must cite supplied source_ids.'
    prompt=f"{schema}\nCLIENT={req.model_dump_json()}\nEVIDENCE={json.dumps(contexts)}\nCRITIQUE={critique}"
    out=client.chat.completions.create(model=settings.llm_model,messages=[{"role":"system","content":"You are a cautious financial-advice drafting agent. Do not invent products or sources."},{"role":"user","content":prompt}],temperature=0).choices[0].message.content
    return json.loads(out.strip().removeprefix("```json").removesuffix("```"))
