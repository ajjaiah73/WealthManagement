"""SQLAlchemy-backed repositories (PostgreSQL in docker-compose, SQLite locally).

Each repository mirrors the method surface of its in-memory counterpart so the
API layer and orchestrator don't care which one they're given. Rows hold the
Pydantic model as JSON; reads re-validate through the domain model.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import AuditEventRow, CaseRow, ClientRow, DocumentRow, ProductRow, UserRow
from app.domain.advisory import AdvisoryCaseRecord
from app.domain.audit import AuditEvent
from app.domain.client import ClientProfile
from app.domain.document import DocumentRecord
from app.domain.product import Product
from app.domain.user import Role, StoredUser


class SqlClientRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def get(self, client_id: str) -> ClientProfile | None:
        with self._sf() as session:
            row = session.get(ClientRow, client_id)
            return ClientProfile.model_validate(row.data) if row else None

    def list(self) -> list[ClientProfile]:
        with self._sf() as session:
            rows = session.scalars(select(ClientRow).order_by(ClientRow.client_id)).all()
            return [ClientProfile.model_validate(r.data) for r in rows]

    def add(self, client: ClientProfile) -> ClientProfile:
        with self._sf.begin() as session:
            session.merge(ClientRow(client_id=client.client_id, data=client.model_dump(mode="json")))
        return client

    def update(self, client: ClientProfile) -> ClientProfile:
        return self.add(client)


class SqlProductRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def get(self, product_id: str) -> Product | None:
        with self._sf() as session:
            row = session.get(ProductRow, product_id)
            return Product.model_validate(row.data) if row else None

    def list(self) -> list[Product]:
        with self._sf() as session:
            rows = session.scalars(select(ProductRow).order_by(ProductRow.product_id)).all()
            return [Product.model_validate(r.data) for r in rows]

    def add(self, product: Product) -> Product:
        with self._sf.begin() as session:
            session.merge(ProductRow(product_id=product.product_id, data=product.model_dump(mode="json")))
        return product


class SqlDocumentRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def get(self, document_id: str) -> DocumentRecord | None:
        with self._sf() as session:
            row = session.get(DocumentRow, document_id)
            return DocumentRecord.model_validate(row.data) if row else None

    def list(self) -> list[DocumentRecord]:
        with self._sf() as session:
            rows = session.scalars(select(DocumentRow).order_by(DocumentRow.document_id)).all()
            return [DocumentRecord.model_validate(r.data) for r in rows]

    def add(self, document: DocumentRecord) -> DocumentRecord:
        with self._sf.begin() as session:
            session.merge(DocumentRow(document_id=document.document_id, data=document.model_dump(mode="json")))
        return document


class SqlAuditRepository:
    """Insert-only. There is deliberately no update/delete method, and the
    table carries database triggers that reject UPDATE/DELETE (see init_db)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def append(self, event: AuditEvent) -> AuditEvent:
        with self._sf.begin() as session:
            session.add(AuditEventRow(
                event_id=event.event_id,
                timestamp=event.timestamp,
                case_id=event.case_id,
                data=event.model_dump(mode="json"),
            ))
        return event

    def list_for_case(self, case_id: str) -> list[AuditEvent]:
        with self._sf() as session:
            rows = session.scalars(
                select(AuditEventRow).where(AuditEventRow.case_id == case_id).order_by(AuditEventRow.seq)
            ).all()
            return [AuditEvent.model_validate(r.data) for r in rows]

    def list_all(self) -> list[AuditEvent]:
        with self._sf() as session:
            rows = session.scalars(select(AuditEventRow).order_by(AuditEventRow.seq)).all()
            return [AuditEvent.model_validate(r.data) for r in rows]


class SqlCaseRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def get(self, case_id: str) -> AdvisoryCaseRecord | None:
        with self._sf() as session:
            row = session.get(CaseRow, case_id)
            return AdvisoryCaseRecord.model_validate(row.data) if row else None

    def list(self) -> list[AdvisoryCaseRecord]:
        with self._sf() as session:
            rows = session.scalars(select(CaseRow).order_by(CaseRow.created_at)).all()
            return [AdvisoryCaseRecord.model_validate(r.data) for r in rows]

    def save(self, record: AdvisoryCaseRecord) -> AdvisoryCaseRecord:
        case = record.case
        with self._sf.begin() as session:
            session.merge(CaseRow(
                case_id=case.case_id,
                client_id=case.client_id,
                status=case.status.value,
                created_at=case.created_at,
                data=record.model_dump(mode="json"),
            ))
        return record


class SqlUserRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def get(self, username: str) -> StoredUser | None:
        with self._sf() as session:
            row = session.get(UserRow, username)
            if row is None:
                return None
            return StoredUser(
                username=row.username, display_name=row.display_name, role=Role(row.role),
                password_hash=row.password_hash,
            )

    def list(self) -> list[StoredUser]:
        with self._sf() as session:
            rows = session.scalars(select(UserRow).order_by(UserRow.username)).all()
            return [
                StoredUser(username=r.username, display_name=r.display_name, role=Role(r.role),
                           password_hash=r.password_hash)
                for r in rows
            ]

    def add(self, user: StoredUser) -> StoredUser:
        with self._sf.begin() as session:
            session.merge(UserRow(
                username=user.username, display_name=user.display_name, role=user.role.value,
                password_hash=user.password_hash,
            ))
        return user
