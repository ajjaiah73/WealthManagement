from fastapi import APIRouter, Depends, HTTPException

from app.container import container
from app.core.security import CurrentUser, require_advisor
from app.domain.client import ClientProfile

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("", response_model=list[ClientProfile])
def list_clients() -> list[ClientProfile]:
    return container.client_repository.list()


@router.post("", response_model=ClientProfile, status_code=201)
def create_client(client: ClientProfile, _: CurrentUser = Depends(require_advisor)) -> ClientProfile:
    if container.client_repository.get(client.client_id):
        raise HTTPException(status_code=409, detail="Client already exists")
    return container.client_repository.add(client)


@router.get("/{client_id}", response_model=ClientProfile)
def get_client(client_id: str) -> ClientProfile:
    client = container.client_repository.get(client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return client
