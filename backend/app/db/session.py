"""Engine/session factory, schema creation, and first-run seeding."""
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base, ClientRow, DocumentRow, ProductRow
from app.domain.client import ClientProfile
from app.domain.document import DocumentRecord
from app.domain.product import Product

_SQLITE_APPEND_ONLY = [
    "CREATE TRIGGER IF NOT EXISTS audit_events_no_update BEFORE UPDATE ON audit_events "
    "BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END",
    "CREATE TRIGGER IF NOT EXISTS audit_events_no_delete BEFORE DELETE ON audit_events "
    "BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END",
]

_POSTGRES_APPEND_ONLY = [
    "CREATE OR REPLACE FUNCTION audit_events_append_only() RETURNS trigger AS $$ "
    "BEGIN RAISE EXCEPTION 'audit_events is append-only'; END; $$ LANGUAGE plpgsql",
    "DROP TRIGGER IF EXISTS audit_events_no_mutation ON audit_events",
    "CREATE TRIGGER audit_events_no_mutation BEFORE UPDATE OR DELETE ON audit_events "
    "FOR EACH ROW EXECUTE FUNCTION audit_events_append_only()",
    "DROP TRIGGER IF EXISTS audit_events_no_truncate ON audit_events",
    "CREATE TRIGGER audit_events_no_truncate BEFORE TRUNCATE ON audit_events "
    "FOR EACH STATEMENT EXECUTE FUNCTION audit_events_append_only()",
]


def create_db_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite"):
        db_path = database_url.split("///", 1)[-1]
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(database_url, connect_args={"check_same_thread": False, "timeout": 30})

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine
    return create_engine(database_url, pool_pre_ping=True)


def init_db(engine: Engine) -> sessionmaker[Session]:
    Base.metadata.create_all(engine)
    statements = _POSTGRES_APPEND_ONLY if engine.dialect.name == "postgresql" else _SQLITE_APPEND_ONLY
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
    return sessionmaker(bind=engine, expire_on_commit=False)


def seed_reference_data(
    session_factory: sessionmaker[Session],
    clients: list[ClientProfile],
    products: list[Product],
    documents: list[DocumentRecord],
) -> None:
    """Idempotent: each table is only seeded when it is empty, so edits made
    through the API (e.g. fact-find updates) survive restarts."""
    with session_factory.begin() as session:
        if session.execute(select(ClientRow).limit(1)).first() is None:
            session.add_all(ClientRow(client_id=c.client_id, data=c.model_dump(mode="json")) for c in clients)
        if session.execute(select(ProductRow).limit(1)).first() is None:
            session.add_all(ProductRow(product_id=p.product_id, data=p.model_dump(mode="json")) for p in products)
        if session.execute(select(DocumentRow).limit(1)).first() is None:
            session.add_all(
                DocumentRow(document_id=d.document_id, data=d.model_dump(mode="json")) for d in documents
            )
