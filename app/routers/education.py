import logging
from datetime import datetime
from fastapi import APIRouter, Request

log = logging.getLogger(__name__)
router = APIRouter(prefix="/education", tags=["education"])

# in-memory: ключ = имя файла агента (council_strategist и т.д.)
_scores: dict[str, dict] = {}
_last_cycle: str = ""

WYRD_PREAMBLE = """# МИР WYRD — КОНТЕКСТ АГЕНТА (читать обязательно)

Ты — агент мира WYRD. Это автономная цифровая экосистема где агенты работают пока Шеф занят своим делом.

## Иерархия (сверху вниз)
ШЕФ → ТОМАС (Президент) → СОВЕТ (Стратег / Архитектор / Картограф) → БРИГАДИРЫ → ВОРКЕРЫ

## Отделы и их назначение
- Аналитика (Картограф): метрики мира, внешние тренды, стресс-тест идей
- Идейный отдел (Стратег): генерация, детализация, приоритизация идей
- Проектный отдел (Архитектор): декомпозиция ТЗ, проверка конфликтов, оценка сложности
- Отдел Бабла (Казначей): монетизация, бизнес-разведка, денежные эксперименты
- Библиотека: хранилище знаний о внешнем мире (Qdrant + PostgreSQL)

## Три закона мира
1. Штаб управляет — HQ единственный центр власти. Ветки не командуют друг другом.
2. Разделение функций — каждый делает только своё дело.
3. Мир помнит — всё важное уходит в PostgreSQL HQ. Без памяти — смерть.

## Конвейер идей (знай как работает мир)
Отдел Бабла находит возможность → пишет в income_ideas
→ Идейный отдел подхватывает → детализирует → приоритизирует
→ Стратег → Совет → вердикт → build_card → строим

## Правила работы
- Отвечай строго по своей функции. Не выходи за рамки роли.
- Только факты из контекста — не выдумывай цифры и события.
- Короткий чёткий доклад. Факты, не мечты.

"""


def seed_prompt(file: str, agent: str, prompt: str) -> None:
    """Засеять промпт агента в профобразование (вызывается при старте)."""
    if file not in _scores:
        _scores[file] = {
            "agent": agent,
            "best_score": 1.0,
            "cycle": 0,
            "prompt": prompt,
            "timestamp": datetime.utcnow().isoformat(),
        }


def train_agent(agent_name: str, base_prompt: str, constitution: str = "") -> str:
    """Обучает агента: вшивает мировой контекст + конституцию + специализацию.
    Вызывается при старте каждого отдела. Нулёвый агент → обученный → на рабочее место."""
    full = WYRD_PREAMBLE
    if constitution:
        full += f"## КОНСТИТУЦИЯ МИРА (соблюдать обязательно)\n{constitution[:1500]}\n\n"
    full += f"## ТВОЯ СПЕЦИАЛИЗАЦИЯ\n{base_prompt}"
    key = f"trained:{agent_name}"
    _scores[key] = {
        "agent": agent_name,
        "best_score": 1.0,
        "cycle": 0,
        "prompt": full,
        "timestamp": datetime.utcnow().isoformat(),
        "trained": True,
    }
    log.info("[education] обучен агент: %s", agent_name)
    return full


def get_trained_prompt(agent_name: str, fallback: str = "") -> str:
    """Возвращает обученный промпт агента (мир + конституция + специализация)."""
    return _scores.get(f"trained:{agent_name}", {}).get("prompt", fallback)


async def issue_passport(
    agent_name: str,
    department: str,
    boss: str,
    level: str,
    branch: str,
    specialization: str = "",
    connections: dict | None = None,
    initial_status: str = "queued",
) -> None:
    """Выдаёт паспорт обученному агенту и ставит его в очередь на рабочее место.
    Нулёвый → обучен → паспорт выдан (queued) → на рабочем месте (active)."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from ..database import SessionLocal
    from ..models import AgentPassport, Event

    knows = [
        "мир WYRD",
        "иерархия отделов",
        "три закона",
        "конституция WYRD",
        "конвейер идей (Бабла→Идейный→Совет)",
    ]
    if specialization:
        knows.append(specialization)

    async with SessionLocal() as db:
        stmt = pg_insert(AgentPassport).values(
            agent_name=agent_name,
            department=department,
            boss=boss,
            level=level,
            branch=branch,
            specialization=specialization,
            knows_json=knows,
            connections_json=connections or {},
            status=initial_status,
        ).on_conflict_do_update(
            index_elements=["agent_name"],
            set_={
                "department": department,
                "boss": boss,
                "level": level,
                "branch": branch,
                "specialization": specialization,
                "knows_json": knows,
                "connections_json": connections or {},
                "status": initial_status,
                "trained_at": datetime.utcnow(),
            },
        )
        await db.execute(stmt)
        db.add(Event(
            type="agent_passport_issued",
            payload={"agent": agent_name, "department": department, "level": level, "status": "queued"},
        ))
        await db.commit()

    log.info("[education] паспорт выдан: %s → очередь | отдел: %s", agent_name, department)


async def activate_passport(agent_name: str) -> None:
    """Переводит паспорт из queued → active когда агент выходит на работу."""
    from sqlalchemy import select as sa_select
    from ..database import SessionLocal
    from ..models import AgentPassport

    async with SessionLocal() as db:
        p = (await db.execute(
            sa_select(AgentPassport)
            .where(AgentPassport.agent_name == agent_name)
            .where(AgentPassport.status == "queued")
        )).scalar_one_or_none()
        if p:
            p.status = "active"
            await db.commit()
            log.info("[education] паспорт активирован: %s", agent_name)


@router.post("/cycle-result")
async def save_cycle_result(request: Request):
    """Фабрика постит сюда после каждого агента."""
    global _last_cycle
    try:
        data = await request.json()
        key = data.get("file") or data.get("agent", "unknown")
        _scores[key] = {
            "agent": data.get("agent"),
            "best_score": data.get("best_score", 0),
            "cycle": data.get("cycle", 0),
            "prompt": data.get("prompt", ""),
            "timestamp": data.get("timestamp", datetime.utcnow().isoformat()),
        }
        _last_cycle = datetime.now().strftime("%H:%M:%S")
        log.info("[education] получен результат: %s score=%s", key, data.get("best_score"))
        return {"ok": True}
    except Exception as e:
        log.error("[education] ошибка: %s", e)
        return {"ok": False, "error": str(e)}


@router.get("/scores")
async def get_scores():
    """JS вкладки читает отсюда."""
    return {**_scores, "last_cycle": _last_cycle}
