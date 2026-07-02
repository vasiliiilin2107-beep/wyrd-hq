"""Ф1/Ф2 арх.v2 — ЦЕЛИ (вход мира) и их жизненный цикл до закрытия.

Вход = только ЦЕЛЬ. Течёт вниз (goal_agent), упирается в исполнение (агент катает /
спек реактора → BuildCard), проходит статусы open→decomposing→awaiting_build→running→
closed. Закрытая ветка уходит под наблюдение Смотрителя, вон из активной иерархии.
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import Goal, BuildCard

router = APIRouter(prefix="/goals", tags=["goals"])

LIFECYCLE = ["open", "decomposing", "awaiting_build", "running", "closed"]
BUILD_DEADLINE_DAYS = 2


def _fmt(g: Goal) -> dict:
    return {
        "id": g.id, "text": g.text, "source": g.source, "status": g.status,
        "terminal": g.terminal, "decomposition": g.decomposition,
        "build_card_id": g.build_card_id, "observer": g.observer, "notes": g.notes,
        "created_at": g.created_at.isoformat() if g.created_at else None,
        "closed_at": g.closed_at.isoformat() if g.closed_at else None,
    }


class GoalIn(BaseModel):
    text: str
    source: str = "chief"       # chief | strategist | frontier
    notes: str | None = None


@router.post("", status_code=201)
async def create_goal(data: GoalIn, session: AsyncSession = Depends(get_session)):
    """ВХОД МИРА: положить ЦЕЛЬ (не идею). Отсюда поток идёт вниз."""
    g = Goal(text=data.text.strip(), source=data.source, status="open", notes=data.notes)
    session.add(g)
    await session.commit()
    await session.refresh(g)
    return {"ok": True, "goal": _fmt(g)}


@router.get("")
async def list_goals(status: str | None = None, session: AsyncSession = Depends(get_session)):
    """Открытые цели — мозг жуёт ТОЛЬКО их, не решённые (эхо запечатано)."""
    q = select(Goal).order_by(desc(Goal.created_at))
    if status:
        q = q.where(Goal.status == status)
    rows = (await session.execute(q)).scalars().all()
    return {"цели": [_fmt(g) for g in rows]}


@router.get("/observed")
async def observed_goals(session: AsyncSession = Depends(get_session)):
    """Закрытые ветки под наблюдением — вне активной иерархии (Ф2)."""
    rows = (await session.execute(
        select(Goal).where(Goal.status == "closed").order_by(desc(Goal.closed_at))
    )).scalars().all()
    return {"наблюдаемые": [_fmt(g) for g in rows]}


@router.post("/{goal_id}/decompose")
async def decompose(goal_id: int, session: AsyncSession = Depends(get_session)):
    """Разложить цель вниз по иерархии → терминал. reactor_spec → карточка Стройки
    (+ найм при дыре в штате); agent_runs → ветка сразу running (агенты катают)."""
    from ..goal_agent import decompose_goal, reactor_spec_text
    g = (await session.execute(select(Goal).where(Goal.id == goal_id))).scalar_one_or_none()
    if not g:
        return {"error": "цель не найдена"}
    g.status = "decomposing"
    await session.commit()

    d = await decompose_goal(g.text, g.source)
    g.decomposition = d
    g.terminal = d.get("terminal", "")

    result = {"goal_id": goal_id, "terminal": g.terminal, "verdict": d.get("verdict", "")}

    if g.terminal == "agent_runs":
        g.status = "running"
        result["итог"] = "агенты катают сами — ветка running"
    elif g.terminal == "reactor_spec":
        # чистый спек реактора → карточка Стройки с дедлайном (Ф6 Томас-петля)
        card = BuildCard(
            session_id=None, kind="goal", agent_name="Цель→Иерархия",
            topic=g.text[:200], tz_text=reactor_spec_text(d),
            summary=d.get("verdict", ""), status="waiting",
            deadline=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=BUILD_DEADLINE_DAYS),
            alert_state="none",
        )
        session.add(card)
        await session.flush()
        g.build_card_id = card.id
        g.status = "awaiting_build"
        result["итог"] = f"спек реактора → карточка Стройки #{card.id} (дедлайн {BUILD_DEADLINE_DAYS}д)"
        # дыра в штате → найм-ТЗ Профессора (Ф5), дедуп внутри propose_hire
        hole = (d.get("hole") or "").strip()
        if hole:
            try:
                from ..professor_agent import propose_hire
                hires = await propose_hire(
                    role=hole[:80], purpose=d.get("verdict", "")[:200],
                    closes=(d.get("reactor_spec") or {}).get("zakryvaet", ""),
                    depends_on=(d.get("reactor_spec") or {}).get("zavisit_ot", ""),
                    first_step=(d.get("reactor_spec") or {}).get("pervyy_shag", ""),
                    from_agent="Профессор")
                result["найм"] = hires
            except Exception as e:
                result["найм_ошибка"] = str(e)
    else:
        g.status = "open"
        result["итог"] = "раскладка не дала терминал — цель осталась открытой"

    await session.commit()
    return result


class StatusIn(BaseModel):
    status: str


@router.post("/{goal_id}/status")
async def set_status(goal_id: int, data: StatusIn, session: AsyncSession = Depends(get_session)):
    """Ручной перевод статуса ветки по жизненному циклу."""
    if data.status not in LIFECYCLE:
        return {"error": f"статус должен быть из {LIFECYCLE}"}
    g = (await session.execute(select(Goal).where(Goal.id == goal_id))).scalar_one_or_none()
    if not g:
        return {"error": "цель не найдена"}
    g.status = data.status
    if data.status == "closed" and not g.closed_at:
        g.closed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        g.observer = g.observer or "Смотритель + Экономдозор"
    await session.commit()
    await session.refresh(g)
    return {"ok": True, "goal": _fmt(g)}


@router.post("/{goal_id}/close")
async def close_goal(goal_id: int, session: AsyncSession = Depends(get_session)):
    """Закрыть ветку на потоке → под наблюдение (Ф2). Вон из активной иерархии;
    Смотритель+Экономдозор следят, карта фронтира открывает соседние клетки."""
    g = (await session.execute(select(Goal).where(Goal.id == goal_id))).scalar_one_or_none()
    if not g:
        return {"error": "цель не найдена"}
    g.status = "closed"
    g.closed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    g.observer = "Смотритель + Экономдозор"
    await session.commit()
    return {"ok": True, "закрыта": _fmt(g),
            "наблюдение": "Смотритель + Экономдозор", "фронтир": "соседние клетки открыты для новой цели"}
