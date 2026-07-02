import os
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from ..database import get_session
from ..models import BuildCard, CouncilSession, ForemanReport, Flag, Goal
from .. import coin

router = APIRouter(prefix="/build", tags=["build"])

VALID_STATUSES = {"waiting", "in_progress", "done"}
# Награда за результат: ТЗ доведено до прода. Монета идёт автору (или Совету для council-карт).
REWARD_PER_BUILD = float(os.environ.get("REWARD_PER_BUILD", "50"))
# Ф6 Томас-петля: карточки стройки, живущие по дедлайну (не council-автопоток)
_ALERT_KINDS = ("goal", "new_hire", "self_upgrade")
PRUNE_GRACE_DAYS = int(os.environ.get("BUILD_PRUNE_GRACE_DAYS", "2"))


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _ping_text(c: BuildCard) -> str:
    first = (c.tz_text or "").strip().splitlines()[0] if c.tz_text else (c.summary or c.topic)
    return f"«{c.topic[:70]}» — {first[:100]}"


class BuildCardUpdate(BaseModel):
    status: str | None = None


class SelfUpgradeIn(BaseModel):
    """ТЗ на саморазвитие от любого агента → раздел самоапгрейда Стройки."""
    agent_name: str
    title: str
    tz_text: str
    summary: str | None = None


def _fmt(c: BuildCard) -> dict:
    return {
        "id": c.id,
        "session_id": c.session_id,
        "kind": getattr(c, "kind", "council"),
        "agent_name": getattr(c, "agent_name", None),
        "topic": c.topic,
        "tz_text": c.tz_text,
        "summary": c.summary,
        "status": c.status,
        "created_at": c.created_at.isoformat(),
        "completed_at": c.completed_at.isoformat() if c.completed_at else None,
    }


@router.get("/queue")
async def get_build_queue(kind: str | None = None, session: AsyncSession = Depends(get_session)):
    verdict_sessions = (await session.execute(
        select(CouncilSession).where(CouncilSession.status == "verdict")
    )).scalars().all()

    existing = (await session.execute(select(BuildCard))).scalars().all()
    existing_ids = {c.session_id for c in existing if c.session_id is not None}

    for s in verdict_sessions:
        if s.id not in existing_ids:
            v = s.verdict_json or {}
            # Ворота: карточку создаём ТОЛЬКО если вратарь решил строить.
            # Старые вердикты без build_decision больше не флудят Стройку.
            bd = v.get("build_decision") or {}
            if not bd.get("build"):
                continue
            session.add(BuildCard(
                session_id=s.id,
                topic=bd.get("title") or s.idea_text,
                # full_tz = ТЗ Архитектора + команда ботов Профессора. Откат на architect для старых вердиктов.
                tz_text=v.get("full_tz") or v.get("architect", ""),
                summary=v.get("summary", ""),
                kind="council",
            ))

    await session.commit()

    q = select(BuildCard).order_by(desc(BuildCard.created_at))
    if kind:
        q = q.where(BuildCard.kind == kind)
    cards = (await session.execute(q)).scalars().all()
    return {"cards": [_fmt(c) for c in cards]}


@router.post("/self-upgrade", status_code=201)
async def add_self_upgrade(data: SelfUpgradeIn, session: AsyncSession = Depends(get_session)):
    """Любой агент пишет сюда ТЗ на саморазвитие — попадает в раздел самоапгрейда Стройки,
    минуя Совет (агент сам знает что в нём ограничивает). Идеи больше не теряются в чате."""
    card = BuildCard(
        session_id=None,
        kind="self_upgrade",
        agent_name=data.agent_name,
        topic=data.title[:200],
        tz_text=data.tz_text,
        summary=data.summary,
        status="waiting",
    )
    session.add(card)
    await session.commit()
    await session.refresh(card)
    return {"ok": True, "card": _fmt(card)}


class NewHireIn(BaseModel):
    """Ф5: иерархия упёрлась в дыру → заявка на найм. Профессор пишет чисто, дедуп."""
    role: str
    purpose: str
    closes: str = ""
    depends_on: str = ""
    first_step: str = ""
    from_agent: str = "Профессор"


@router.post("/new-hire", status_code=201)
async def add_new_hire(data: NewHireIn):
    """Профессор кладёт чистую заявку на найм (kind=new_hire), с дедупом против штата.
    Дальше Томас алертит Шефу, Шеф строит. Для ролей, требующих кода/инструментов."""
    from ..professor_agent import propose_hire
    res = await propose_hire(data.role, data.purpose, data.closes,
                             data.depends_on, data.first_step, data.from_agent)
    return res


@router.get("/new-hires")
async def list_new_hires(session: AsyncSession = Depends(get_session)):
    """Открытые заявки на найм — что миру не хватает, ждёт стройки."""
    rows = (await session.execute(
        select(BuildCard).where(BuildCard.kind == "new_hire").order_by(desc(BuildCard.created_at))
    )).scalars().all()
    return {"наймы": [_fmt(c) for c in rows]}


@router.get("/foreman")
async def get_foreman_reports(limit: int = 10, session: AsyncSession = Depends(get_session)):
    reports = (await session.execute(
        select(ForemanReport).order_by(desc(ForemanReport.checked_at)).limit(limit)
    )).scalars().all()
    return {"reports": [
        {
            "id": r.id,
            "checked_at": r.checked_at.isoformat(),
            "stuck_count": r.stuck_count,
            "analysis": r.analysis,
            "task_ids": r.task_ids or [],
        }
        for r in reports
    ]}


@router.post("/cleanup")
async def cleanup_legacy_cards(session: AsyncSession = Depends(get_session)):
    """Удаляет waiting-карточки легаси-флуда: вердикты БЕЗ build_decision.build=true.
    Гейтнутые вердикты (ворота с201) сохраняются. in_progress/done не трогаются."""
    cards = (await session.execute(
        select(BuildCard).where(BuildCard.status == "waiting")
    )).scalars().all()
    sessions = (await session.execute(select(CouncilSession))).scalars().all()
    gated = {s.id for s in sessions
             if (s.verdict_json or {}).get("build_decision", {}).get("build")}
    removed = 0
    for c in cards:
        # самоапгрейд и найм-карточки не трогаем — они без сессии, созданы агентами
        if c.kind in ("self_upgrade", "new_hire"):
            continue
        if c.session_id not in gated:
            await session.delete(c)
            removed += 1
    await session.commit()
    return {"removed": removed, "kept_gated_sessions": len(gated)}


@router.get("/alerts")
async def build_alerts(session: AsyncSession = Depends(get_session)):
    """Ф6 ТОМАС-ПЕТЛЯ: два повода, ОДИН пинг на состояние.
    1) новая карта стройки (kind goal/new_hire/self_upgrade, ждёт) → пинг «ТЗ лежит»;
    2) дедлайн прошёл, всё ещё не построено → пинг «строим/удаляем?».
    Каждый пинг ставит alert_state, чтобы не долбить повторно. Поднимает Flag для Томаса."""
    now = _now()
    cards = (await session.execute(
        select(BuildCard).where(BuildCard.kind.in_(_ALERT_KINDS), BuildCard.status == "waiting")
    )).scalars().all()
    new_pings, overdue_pings = [], []
    for c in cards:
        if c.alert_state == "none":
            c.alert_state = "announced"
            txt = f"🏗 Стройка ждёт: {_ping_text(c)}. ТЗ лежит (карта #{c.id}, дедлайн " \
                  f"{c.deadline.strftime('%d.%m') if c.deadline else '—'})."
            new_pings.append({"card_id": c.id, "текст": txt})
            session.add(Flag(title=f"Стройка #{c.id}: {c.topic[:80]}", body=txt,
                             type="todo", component="thomas", anchor="hq.build.new",
                             status="active", author="Иерархия"))
        elif c.alert_state == "announced" and c.deadline and c.deadline < now:
            c.alert_state = "overdue"
            txt = f"⏰ Просрочка: {_ping_text(c)} (карта #{c.id}). Дедлайн прошёл, не построено — " \
                  f"СТРОИМ или УДАЛЯЕМ? Если молчок — прунинг через {PRUNE_GRACE_DAYS}д."
            overdue_pings.append({"card_id": c.id, "текст": txt})
            session.add(Flag(title=f"Просрочка стройки #{c.id}: {c.topic[:70]}", body=txt,
                             type="risk", component="thomas", anchor="hq.build.overdue",
                             status="active", author="Иерархия"))
    await session.commit()
    return {"новые": new_pings, "просроченные": overdue_pings,
            "итог": f"{len(new_pings)} новых пингов, {len(overdue_pings)} просрочек"}


@router.post("/prune")
async def prune_overdue(session: AsyncSession = Depends(get_session)):
    """Ф6 ПРУНИНГ: карта просрочена + прошёл grace после 2-го пинга, а Шеф не построил →
    очередь чистится сама. Карта удаляется, связанная цель закрывается (не построено).
    Чистит ТОЛЬКО goal/new_hire/self_upgrade — council-автопоток не трогаем."""
    now = _now()
    cards = (await session.execute(
        select(BuildCard).where(BuildCard.kind.in_(_ALERT_KINDS),
                                BuildCard.status == "waiting",
                                BuildCard.alert_state == "overdue")
    )).scalars().all()
    pruned = []
    for c in cards:
        if not c.deadline or c.deadline + timedelta(days=PRUNE_GRACE_DAYS) > now:
            continue
        # связанная цель → закрыть как «не построено» (вон из активной иерархии)
        g = (await session.execute(
            select(Goal).where(Goal.build_card_id == c.id))).scalar_one_or_none()
        if g:
            g.status = "closed"
            g.closed_at = now
            g.observer = "прунинг — не построено к дедлайну"
        pruned.append({"card_id": c.id, "topic": c.topic[:80], "goal_id": g.id if g else None})
        await session.delete(c)
    await session.commit()
    return {"вырезано": len(pruned), "карты": pruned}


@router.patch("/queue/{card_id}")
async def update_build_card(
    card_id: int,
    data: BuildCardUpdate,
    session: AsyncSession = Depends(get_session),
):
    card = (await session.execute(
        select(BuildCard).where(BuildCard.id == card_id)
    )).scalar_one_or_none()
    if not card:
        return {"error": "not found"}
    rewarded = None
    if data.status and data.status in VALID_STATUSES:
        if data.status == "done" and card.status != "done":
            card.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            # Награда ЗА РЕЗУЛЬТАТ: ТЗ доведено до прода. Из пула (нет пула → дефицит).
            author = card.agent_name or "Совет"
            rewarded = await coin.reward(author, REWARD_PER_BUILD, ref=f"ТЗ#{card.id}: {card.topic[:80]}")
        card.status = data.status
    await session.commit()
    await session.refresh(card)
    out = _fmt(card)
    if rewarded is not None:
        out["награда"] = rewarded
    return out
