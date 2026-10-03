import asyncio
import json
import logging
import time
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.container import container
from app.core.rate_limit import advisory_rate_limiter
from app.core.security import CurrentUser, require_advisor
from app.domain.advisory import AdvisoryCase, AdvisoryCaseRecord
from app.domain.client import ClientProfile
from app.domain.retrieval import RetrievedDocument
from app.graph.orchestrator import DEFAULT_REQUEST, TERMINAL_STATUSES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/advisory", tags=["advisory"])

STREAM_POLL_SECONDS = 0.25
STREAM_TIMEOUT_SECONDS = 600


class AdvisoryRunRequest(BaseModel):
    client_id: str
    request: str = Field(default=DEFAULT_REQUEST, max_length=2000)


class AdvisoryCaseDetail(BaseModel):
    case: AdvisoryCase
    request: str | None = None
    goal: str | None = None
    constraints: list[str] = []
    retrieval_query: str | None = None
    graph_context: list[str] = []
    critique_notes: list[str] = []
    current_step: str | None = None


def _client_or_404(client_id: str) -> ClientProfile:
    client = container.client_repository.get(client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


def _record_or_404(case_id: str) -> AdvisoryCaseRecord:
    record = container.case_repository.get(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Advisory case not found")
    return record


def _execute(record: AdvisoryCaseRecord, client: ClientProfile, session_id: str) -> AdvisoryCaseRecord:
    return container.pipeline.execute(record, client, container.product_repository.list(), session_id)


@router.post("/run", response_model=AdvisoryCase, status_code=201, dependencies=[Depends(advisory_rate_limiter)])
def run_advisory(payload: AdvisoryRunRequest, _: CurrentUser = Depends(require_advisor)) -> AdvisoryCase:
    """Runs the full LangGraph pipeline synchronously and returns the final case."""
    client = _client_or_404(payload.client_id)
    record = container.pipeline.create_case(client, payload.request)
    return _execute(record, client, str(uuid.uuid4())).case


@router.post("/start", response_model=AdvisoryCase, status_code=202, dependencies=[Depends(advisory_rate_limiter)])
def start_advisory(payload: AdvisoryRunRequest, _: CurrentUser = Depends(require_advisor)) -> AdvisoryCase:
    """Queues the pipeline in the background and returns immediately (status IN_PROGRESS).
    Follow progress live via GET /api/advisory/{case_id}/stream."""
    client = _client_or_404(payload.client_id)
    record = container.pipeline.create_case(client, payload.request)
    container.executor.submit(_execute, record, client, str(uuid.uuid4()))
    return record.case


@router.get("", response_model=list[AdvisoryCase])
def list_advisory_cases() -> list[AdvisoryCase]:
    return [record.case for record in container.case_repository.list()]


@router.get("/graph")
def get_pipeline_graph() -> dict[str, str]:
    """Mermaid rendering of the compiled LangGraph StateGraph."""
    return {"mermaid": container.pipeline.mermaid()}


@router.get("/{case_id}", response_model=AdvisoryCase)
def get_advisory_case(case_id: str) -> AdvisoryCase:
    return _record_or_404(case_id).case


@router.get("/{case_id}/detail", response_model=AdvisoryCaseDetail)
def get_advisory_case_detail(case_id: str) -> AdvisoryCaseDetail:
    r = _record_or_404(case_id)
    return AdvisoryCaseDetail(
        case=r.case, request=r.request, goal=r.goal, constraints=r.constraints, retrieval_query=r.retrieval_query,
        graph_context=r.graph_context, critique_notes=r.critique_notes, current_step=r.current_step,
    )


@router.get("/{case_id}/retrieval", response_model=list[RetrievedDocument])
def get_retrieved_evidence(case_id: str) -> list[RetrievedDocument]:
    return _record_or_404(case_id).retrieved_documents


@router.get("/{case_id}/stream")
async def stream_advisory_case(case_id: str, request: Request) -> StreamingResponse:
    """Server-Sent Events: one `data:` message per audit event as each LangGraph node
    completes, then `event: done` carrying the final case. Works both while the
    pipeline is running (live) and for completed cases (immediate replay)."""
    _record_or_404(case_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        sent = 0
        deadline = time.monotonic() + STREAM_TIMEOUT_SECONDS
        while True:
            # Read status before events: events are written before the terminal status
            # is saved, so a terminal status guarantees the event list below is complete.
            record = await asyncio.to_thread(container.case_repository.get, case_id)
            events = await asyncio.to_thread(container.audit_repository.list_for_case, case_id)
            for event in events[sent:]:
                yield f"data: {event.model_dump_json()}\n\n"
            sent = len(events)
            if record is not None and record.case.status in TERMINAL_STATUSES:
                yield f"event: done\ndata: {record.case.model_dump_json()}\n\n"
                return
            if time.monotonic() > deadline:
                yield f"event: timeout\ndata: {json.dumps({'case_id': case_id})}\n\n"
                return
            if await request.is_disconnected():
                return
            await asyncio.sleep(STREAM_POLL_SECONDS)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
