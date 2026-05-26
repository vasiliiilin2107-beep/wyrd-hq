from datetime import datetime
from typing import Any
from sqlalchemy import String, JSON, ForeignKey, DateTime, func, Text, BigInteger, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    url: Mapped[str | None] = mapped_column(String(500))
    version: Mapped[str | None] = mapped_column(String(50))
    last_seen: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(String(20), default="online")

    events: Mapped[list["Event"]] = relationship(back_populates="branch")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), index=True)
    type: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    branch: Mapped["Branch | None"] = relationship(back_populates="events")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="todo")  # todo | in_progress | done
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Backup(Base):
    __tablename__ = "backups"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    status: Mapped[str] = mapped_column(String(20), default="ok")
    location: Mapped[str | None] = mapped_column(Text)
    components: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    trigger: Mapped[str] = mapped_column(String(50), default="cron")


class Flag(Base):
    __tablename__ = "flags"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str | None] = mapped_column(Text)
    # anchor|beacon|dependency|idea|todo|risk|note
    type: Mapped[str] = mapped_column(String(50), default="note", index=True)
    # hq|thomas|studio|library|quarantine|global
    component: Mapped[str] = mapped_column(String(100), default="global", index=True)
    # путь внутри компонента: "thomas.memory.facts", "hq.events.redis"
    anchor: Mapped[str | None] = mapped_column(String(500))
    # active|done|archived
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    author: Mapped[str] = mapped_column(String(100), default="moz")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
