"""Repository contracts. Both the in-memory implementations (unit tests) and the
SQLAlchemy implementations in app.repositories.sql (PostgreSQL/SQLite) satisfy
these Protocols, so callers never depend on the storage backend."""
from typing import Protocol, TypeVar

from app.domain.advisory import AdvisoryCaseRecord
from app.domain.audit import AuditEvent
from app.domain.client import ClientProfile
from app.domain.document import DocumentRecord
from app.domain.product import Product

T = TypeVar("T")


class Repository(Protocol[T]):
    def get(self, entity_id: str) -> T | None: ...

    def list(self) -> list[T]: ...

    def add(self, entity: T) -> T: ...


class ClientSource(Protocol):
    def get(self, client_id: str) -> ClientProfile | None: ...

    def list(self) -> list[ClientProfile]: ...

    def add(self, client: ClientProfile) -> ClientProfile: ...

    def update(self, client: ClientProfile) -> ClientProfile: ...


class ProductSource(Protocol):
    def get(self, product_id: str) -> Product | None: ...

    def list(self) -> list[Product]: ...


class DocumentSource(Protocol):
    def get(self, document_id: str) -> DocumentRecord | None: ...

    def list(self) -> list[DocumentRecord]: ...


class AuditSink(Protocol):
    """Append-only: no update or delete in the contract."""

    def append(self, event: AuditEvent) -> AuditEvent: ...

    def list_for_case(self, case_id: str) -> list[AuditEvent]: ...

    def list_all(self) -> list[AuditEvent]: ...


class CaseStore(Protocol):
    def get(self, case_id: str) -> AdvisoryCaseRecord | None: ...

    def list(self) -> list[AdvisoryCaseRecord]: ...

    def save(self, record: AdvisoryCaseRecord) -> AdvisoryCaseRecord: ...
