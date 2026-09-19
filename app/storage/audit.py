import json, uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from app.config import settings

def init_db():
    try:
        e=create_engine(settings.mysql_url,pool_pre_ping=True)
        with e.begin() as c:
            c.execute(text("CREATE TABLE IF NOT EXISTS audit_log (audit_id VARCHAR(64) PRIMARY KEY, client_id VARCHAR(128), created_at DATETIME, request_json JSON, response_json JSON, compliant BOOLEAN)"))
        return True
    except Exception: return False

def save_audit(req, response):
    aid=str(uuid.uuid4()); response["audit_id"]=aid
    try:
        e=create_engine(settings.mysql_url,pool_pre_ping=True)
        with e.begin() as c:
            c.execute(text("CREATE TABLE IF NOT EXISTS audit_log (audit_id VARCHAR(64) PRIMARY KEY, client_id VARCHAR(128), created_at DATETIME, request_json JSON, response_json JSON, compliant BOOLEAN)"))
            c.execute(text("INSERT INTO audit_log VALUES (:a,:c,:t,:r,:s,:ok)"),{"a":aid,"c":req.client.client_id,"t":datetime.now(timezone.utc).replace(tzinfo=None),"r":json.dumps(req.model_dump()),"s":json.dumps(response),"ok":response["compliant"]})
    except Exception:
        response.setdefault("audit_notes",[]).append("MySQL unavailable; audit ID generated but record was not persisted.")
    return response
