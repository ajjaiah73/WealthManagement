from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ValidationError

from app.container import container
from app.core.security import CurrentUser, require_advisor
from app.domain.client import ClientProfile, FactFind, build_fact_find

router = APIRouter(prefix="/api/fact-find", tags=["fact-find"])

IMMUTABLE_FIELDS = {"client_id"}


class FactFindSubmission(BaseModel):
    client_id: str
    updates: dict[str, Any] = {}


@router.post("", response_model=FactFind)
def submit_fact_find(submission: FactFindSubmission, _: CurrentUser = Depends(require_advisor)) -> FactFind:
    client = container.client_repository.get(submission.client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    requested = set(submission.updates)
    rejected = sorted((requested - set(ClientProfile.model_fields)) | (requested & IMMUTABLE_FIELDS))
    if rejected:
        raise HTTPException(status_code=422, detail=f"Fields cannot be updated: {', '.join(rejected)}")
    try:
        updated = ClientProfile.model_validate({**client.model_dump(), **submission.updates})
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=jsonable_encoder(exc.errors())) from exc
    container.client_repository.update(updated)
    return build_fact_find(updated)


@router.get("/{client_id}", response_model=FactFind)
def get_fact_find(client_id: str) -> FactFind:
    client = container.client_repository.get(client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return build_fact_find(client)
