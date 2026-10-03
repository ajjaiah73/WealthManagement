
from app.domain.client import ClientProfile


class InMemoryClientRepository:
    def __init__(self, clients: list[ClientProfile]) -> None:
        self._clients: dict[str, ClientProfile] = {c.client_id: c for c in clients}

    def get(self, client_id: str) -> ClientProfile | None:
        return self._clients.get(client_id)

    def list(self) -> list[ClientProfile]:
        return list(self._clients.values())

    def add(self, client: ClientProfile) -> ClientProfile:
        self._clients[client.client_id] = client
        return client

    def update(self, client: ClientProfile) -> ClientProfile:
        self._clients[client.client_id] = client
        return client
