from datetime import datetime

from pydantic import BaseModel


class AuditEvent(BaseModel):
    event_id: str
    timestamp: datetime
    session_id: str
    client_id: str | None = None
    case_id: str | None = None
    agent: str
    action: str
    model: str | None = None
    model_version: str | None = None
    prompt_version: str | None = None
    input_reference: str | None = None
    output_reference: str | None = None
    iteration: int = 0
    status: str  # "success" | "failure"
    details: str | None = None
