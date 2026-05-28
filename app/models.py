from datetime import datetime
from typing import Any
from sqlalchemy import String, JSON, ForeignKey, DateTime, func, Text, BigInteger, ARRAY, Float
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


class TechTask(Base):
    __tablename__ = "tech_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    # pending | running | waiting_approval | done | failed
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    result: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(100), default="thomas")
    priority: Mapped[int] = mapped_column(default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


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


class IncomeIdea(Base):
    __tablename__ = "income_ideas"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(100), default="thomas")
    # idea | testing | active | archived
    status: Mapped[str] = mapped_column(String(30), default="idea", index=True)
    expected_revenue: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    experiments: Mapped[list["IncomeExperiment"]] = relationship(back_populates="idea")


class IncomeExperiment(Base):
    __tablename__ = "income_experiments"

    id: Mapped[int] = mapped_column(primary_key=True)
    idea_id: Mapped[int | None] = mapped_column(ForeignKey("income_ideas.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    hypothesis: Mapped[str | None] = mapped_column(Text)
    # running | paused | success | fail
    status: Mapped[str] = mapped_column(String(30), default="running", index=True)
    result: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    idea: Mapped["IncomeIdea | None"] = relationship(back_populates="experiments")


class AgentRule(Base):
    __tablename__ = "agent_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule: Mapped[str] = mapped_column(Text)
    # thomas | technik | studio | all
    audience: Mapped[str] = mapped_column(String(50), default="all", index=True)
    # tech_task_done | tech_task_failed | manual | patrol | ...
    source: Mapped[str] = mapped_column(String(100), default="manual")
    source_ref: Mapped[str | None] = mapped_column(String(200))  # task_id, event_id и т.д.
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UserToken(Base):
    __tablename__ = "user_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(200))
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    transactions: Mapped[list["TokenTransaction"]] = relationship(back_populates="user")


class TokenTransaction(Base):
    __tablename__ = "token_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user_tokens.chat_id"), index=True)
    amount: Mapped[float] = mapped_column(Float)  # + пополнение, - списание
    reason: Mapped[str | None] = mapped_column(String(500))
    service: Mapped[str] = mapped_column(String(100), default="scribe")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    user: Mapped["UserToken"] = relationship(back_populates="transactions")
