"""SQLAlchemy models for the Griffin backend.

The schema mirrors REQUIREMENTS.md section 7. UUID primary keys are stored as
strings so the same models work on SQLite (offline default) and PostgreSQL. JSON
columns use the portable JSON type on SQLite and JSONB on PostgreSQL.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

# Portable JSON type: plain JSON on SQLite, JSONB on PostgreSQL (per the spec).
JSONType = JSON().with_variant(JSONB, "postgresql")


def new_uuid() -> str:
    """Return a fresh UUID as a string primary key."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Return the current time as a timezone aware UTC datetime."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class Project(Base):
    """A single generation run: one prompt turns into one project."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(Text, default="")
    root_path: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    offices: Mapped[list["Office"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "root_path": self.root_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Office(Base):
    """An office node in the chain and its most recent status for a project."""

    __tablename__ = "offices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"))
    role: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="idle")
    current_context: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)

    project: Mapped["Project"] = relationship(back_populates="offices")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "role": self.role,
            "status": self.status,
            "current_context": self.current_context,
        }


class Message(Base):
    """A chat or status message emitted while a project is generated."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"))
    office_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("offices.id"), nullable=True
    )
    channel: Mapped[str] = mapped_column(Text, default="#general")
    content: Mapped[str] = mapped_column(Text, default="")
    artifacts: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    project: Mapped["Project"] = relationship(back_populates="messages")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "office_id": self.office_id,
            "channel": self.channel,
            "content": self.content,
            "artifacts": self.artifacts,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
