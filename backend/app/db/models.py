"""SQLAlchemy table definitions.

Domain objects are stored as validated JSON documents alongside indexed key
columns, so the Pydantic models in app.domain stay the single source of truth
for shape while queries (by case, by client, chronological audit) stay indexed.
Works unchanged on PostgreSQL (docker-compose) and SQLite (local default).
"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ClientRow(Base):
    __tablename__ = "clients"
    client_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)


class ProductRow(Base):
    __tablename__ = "products"
    product_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)


class DocumentRow(Base):
    __tablename__ = "documents"
    document_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)


class CaseRow(Base):
    __tablename__ = "advisory_cases"
    case_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    client_id: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)  # AdvisoryCaseRecord


class AuditEventRow(Base):
    """Append-only: the repository exposes no update/delete, and init_db adds
    database triggers that reject UPDATE and DELETE on this table."""

    __tablename__ = "audit_events"
    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    case_id: Mapped[str | None] = mapped_column(String(32), index=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)


class UserRow(Base):
    __tablename__ = "users"
    username: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(String(128))
