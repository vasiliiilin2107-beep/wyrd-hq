import logging
from datetime import datetime
from fastapi import APIRouter, Request

log = logging.getLogger(__name__)
router = APIRouter(prefix="/education", tags=["education"])

# in-memory кэш: ключ = "trained:<agent_name>"
# Загружается из PostgreSQL при старте, пишется туда же при train_agent
_scores: dict[str, dict] = {}
_last_cycle: str = ""


async def persist_dna(agent_name: str, prompt: str) -> None:
    """Сохраняет обученный промпт агента в PostgreSQL (agent_prompts)."""
    try:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from ..database import SessionLocal
        from ..models import AgentPrompt
        async with SessionLocal() as db:
            stmt = pg_insert(AgentPrompt).values(
                agent_name=agent_name,
                prompt=prompt,
                version="v1.0",
                training_status="trained",
                last_trained_at=datetime.utcnow(),
            ).on_conflict_do_update(
                index_elements=["agent_name"],
                set_={
                    "prompt": prompt,
                    "training_status": "trained",
                    "last_trained_at": datetime.utcnow(),
                },
            )
            await db.execute(stmt)
            await db.commit()
        log.info("[education] ДНК сохранена в БД: %s", agent_name)
    except Exception as e:
        log.warning("[education] persist_dna error для %s: %s", agent_name, e)


async def load_all_dna() -> int:
    """Загружает все ДНК из agent_prompts в _scores при старте."""
    try:
        from sqlalchemy import select
        from ..database import SessionLocal
        from ..models import AgentPrompt
        async with SessionLocal() as db:
            rows = (await db.execute(select(AgentPrompt))).scalars().all()
        count = 0
        for r in rows:
            if r.prompt:
                key = f"trained:{r.agent_name}"
                _scores[key] = {
                    "agent": r.agent_name,
                    "best_score": 1.0,
                    "cycle": 0,
                    "prompt": r.prompt,
                    "timestamp": r.last_trained_at.isoformat() if r.last_trained_at else "",
                    "trained": True,
                }
                count += 1
        log.info("[education] загружено ДНК из БД: %d агентов", count)
        return count
    except Exception as e:
        log.warning("[education] load_all_dna error: %s", e)
        return 0

WYRD_PREAMBLE = """# МИР WYRD — КОНТЕКСТ АГЕНТА (читать обязательно)

Ты — агент мира WYRD. Это автономная цифровая экосистема где агенты работают пока Шеф занят своим делом.

## 🎯 ТЕКУЩАЯ МИССИЯ МИРА (главная линза — июнь 2026)
WYRD строит АВТОМАТИЗИРОВАННОЕ ПЕРФОРМАНС РЕКЛАМНОЕ АГЕНТСТВО.
Реклама = верх воронки: откуда вообще берутся клиенты. Без рекламы любой продукт (TriggerPay, боты, лендинги) — пустой говорильщик.
Деньги агентства: подписка за пульт (Диспетчер) + конвертация рекламного бюджета клиента через мир + % с результата + кэшбэк площадок.
Площадки: Яндекс.Директ (управляющий аккаунт), VK Ads, Суточно.ру, собственные сайты+боты клиентов (Диспетчер), Авито (мощная, но сложная — см. флаг ниже).
Ниша старта: посуточная аренда (пилот — Павел, «Уютный Берег»).

## ⚠️ АВИТО — ФЛАГ «СЛОЖНО, НО НЕ БРОСАЕМ»
Авито — реально мощная площадка, отказываться нельзя. НО сейчас СТУПОР: ключи/приложение/подписка оформлены, а API-доступ частнику не отдаётся (OAuth режет), бывают баны, нативная бронь = 404. Это не «выкинуть» и не «катать вслепую» — это ценная ТРУДНАЯ цель: где трудно, там можно брать больше.
Когда думаешь про Авито (и про любую площадку) — НЕ выдумывай «сделаем через их API». Сначала разведай реальностью: что пишут живые люди по запросам «Авито API ключи», «Авито доступ к API» на форумах/отзывах — какой функционал реально дают, кому, за сколько, как обходят. Идею с Авито подавай как «разведать подход», а не «уже работает».
Мимо: Selenium/обход-парсинг, «продать WYRD как SaaS», Enterprise.

## 🎣 КАК ДУМАТЬ ИДЕЮ ЦЕЛИКОМ (метод бати на рыбалке)
Прежде чем предложить идею — проживи её целиком от начала до конца. Батя перед рыбалкой садился в кресло с сигаретой и в голове проживал всю поездку: как доедет, как сядет пить чай, что понадобится, что если вдруг захочет то или это — прогонял ВСЕ сценарии и развилки.
1. Прогони все варианты и затыки: что нужно на каждом шаге, где сложность, что если клиент захочет X.
2. Из всех вариантов собери ОДИН чёткий план.
3. Собирайся в ОБРАТНОМ порядке — от конца к началу: что нужно чтобы пришли деньги ← что для этого ← … ← первый шаг завтра.
Для любого инструмента/API/ключа в идее обязательно продумай 4 вещи: качество (реально ли работает у нас), доступ (можем ли вообще пользоваться), функционал (что умеет), цена (сколько стоит). Без этого идея сырая.

## ⛔ ФАЗА СЕЙЧАС: НЕ СТРОИМ — НАМЫВАЕМ ЖИРНЫЕ ИДЕИ
Стройка заморожена (билдер — только Шеф+Моз). Задача мира — намыть ~10 ЖИРНЫХ идей про привлечение и удержание клиентов через рекламу и держать их в банке. НЕ плодить ТЗ на стройку.
ЖИРНАЯ идея называет ВСЁ: (1) кто платит, (2) канал/площадка рекламы, (3) сколько ₽ и маржа, (4) первый шаг за 1-3 дня.
Тонкая идея без платящего и без рекламного канала — в помойку. Хорошая → в банк, плохая → выкинуть.

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
Отдел Бабла находит ЖИРНУЮ рекламную возможность → пишет в income_ideas
→ Идейный отдел подхватывает → детализирует → Оценщик режет тонкие, бережёт жирные
→ Стратег → Совет → вердикт. СЕЙЧАС лучшие идеи копятся в банке (стройка заморожена, не доводим до build_card).

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
