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


class Constitution(Base):
    __tablename__ = "constitution"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    text: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CouncilSession(Base):
    __tablename__ = "council_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    idea_text: Mapped[str] = mapped_column(Text)
    # pending | thinking | verdict | done
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    verdict_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    # manual | autonomous | thomas
    source: Mapped[str] = mapped_column(String(50), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    messages: Mapped[list["CouncilMessage"]] = relationship(back_populates="session")


class CouncilMessage(Base):
    __tablename__ = "council_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("council_sessions.id"), index=True)
    # strategist | architect | cartographer
    speaker: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped["CouncilSession"] = relationship(back_populates="messages")


class CouncilThought(Base):
    __tablename__ = "council_thoughts"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(50), default="council")
    tags: Mapped[list[str] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(200))
    # council | foreman | worker | observer
    level: Mapped[str] = mapped_column(String(50), default="worker", index=True)
    # строительство | идеи | наука | контент | global
    branch: Mapped[str] = mapped_column(String(100), default="global", index=True)
    # active | idle | offline
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    current_task: Mapped[str | None] = mapped_column(Text)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    can_propose: Mapped[bool] = mapped_column(default=True)
    last_pulse: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_agent: Mapped[str] = mapped_column(String(100), index=True)
    role_needed: Mapped[str] = mapped_column(String(200))
    reason: Mapped[str | None] = mapped_column(Text)
    # pending | approved | rejected | building | done
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ForemanReport(Base):
    __tablename__ = "foreman_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    stuck_count: Mapped[int] = mapped_column(default=0)
    analysis: Mapped[str] = mapped_column(Text)
    task_ids: Mapped[list[int] | None] = mapped_column(JSON)


class BuildCard(Base):
    __tablename__ = "build_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    # council-карточки ссылаются на сессию; self_upgrade — session_id=NULL
    session_id: Mapped[int | None] = mapped_column(ForeignKey("council_sessions.id"), unique=True, index=True, nullable=True)
    topic: Mapped[str] = mapped_column(Text)
    tz_text: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    # council | self_upgrade — раздел Стройки
    kind: Mapped[str] = mapped_column(String(30), default="council", index=True)
    # кто предложил self_upgrade ТЗ (thomas, смотритель, …)
    agent_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # waiting | in_progress | done
    status: Mapped[str] = mapped_column(String(30), default="waiting", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AnalyticsReport(Base):
    __tablename__ = "analytics_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    period_hours: Mapped[int] = mapped_column(default=24)
    metrics_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    analysis: Mapped[str] = mapped_column(Text)


class AgentReport(Base):
    __tablename__ = "agent_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_name: Mapped[str] = mapped_column(String(100), index=True)
    branch: Mapped[str] = mapped_column(String(100), index=True)
    report: Mapped[str] = mapped_column(Text)
    checked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class AgentPassport(Base):
    __tablename__ = "agent_passports"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    department: Mapped[str] = mapped_column(String(200))
    boss: Mapped[str] = mapped_column(String(100))
    level: Mapped[str] = mapped_column(String(50))
    branch: Mapped[str] = mapped_column(String(100))
    specialization: Mapped[str | None] = mapped_column(Text)
    knows_json: Mapped[list[str] | None] = mapped_column(JSON)
    connections_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    # queued | active | revoked
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    trained_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    issued_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AgentPrompt(Base):
    __tablename__ = "agent_prompts"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    prompt: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(20), default="v1.0")
    # idle | queued | in_training | done
    training_status: Mapped[str] = mapped_column(String(30), default="idle")
    last_trained_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AgentJournal(Base):
    __tablename__ = "agent_journal"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_name: Mapped[str] = mapped_column(String(100), index=True)
    # update | error | repair | downtime | training
    entry_type: Mapped[str] = mapped_column(String(30), index=True)
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(100), default="hq_panel")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class IdeaDeptReport(Base):
    __tablename__ = "idea_dept_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    metrics_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    analysis: Mapped[str] = mapped_column(Text)


class ProjectDeptReport(Base):
    __tablename__ = "project_dept_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    metrics_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    analysis: Mapped[str] = mapped_column(Text)


class BablaReport(Base):
    __tablename__ = "babla_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    metrics_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    analysis: Mapped[str] = mapped_column(Text)


class EnergyLedger(Base):
    """Счётчик энергии: КАЖДЫЙ импульс LLM — кто, вход/выход токенов, ₽. Не в куче."""
    __tablename__ = "energy_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    caller: Mapped[str] = mapped_column(String(100), index=True, default="hq")
    model: Mapped[str] = mapped_column(String(120), default="")
    tokens_in: Mapped[int] = mapped_column(default=0)    # входящий импульс (prompt)
    tokens_out: Mapped[int] = mapped_column(default=0)   # исходящий импульс (completion)
    cost_rub: Mapped[float] = mapped_column(default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class LedgerEntry(Base):
    """Бухгалтерия мира: реальные ₽ вход/выход (доход/расход) — для Казначея."""
    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    direction: Mapped[str] = mapped_column(String(10), index=True)  # in | out
    category: Mapped[str] = mapped_column(String(50), index=True)   # llm | server | revenue | other
    amount_rub: Mapped[float] = mapped_column(default=0.0)
    note: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


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
