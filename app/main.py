from fastapi import FastAPI, HTTPException
from app.models import AdviceRequest, AdviceResponse
from app.workflow import advisory_graph
from app.storage.audit import save_audit, init_db
app=FastAPI(title="Financial Advisor Agentic RAG",version="1.0.0")
@app.on_event("startup")
def startup(): init_db()
@app.get("/health")
def health(): return {"status":"ok"}
@app.post("/advice",response_model=AdviceResponse)
def advice(req: AdviceRequest):
    try:
        state=advisory_graph.invoke({"request":req,"reflection_count":0})
        return save_audit(req,state["final"])
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
