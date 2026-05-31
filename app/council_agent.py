import asyncio
import logging
import os

import httpx
from sqlalchemy import select, desc

from .database import SessionLocal
from .models import Agent, CouncilMessage, CouncilSession, CouncilThought, IncomeIdea, TechTask

log = logging.getLogger(__name__)

POLZA_URL = "https://polza.ai/api/v1/chat/completions"
POLZA_KEY = os.environ.get("POLZA_API_KEY", "")
MODEL = "deepseek/deepseek-v4-flash"

SYS_STRATEGIST = """# Системный промпт для агента «Стратег Совета мира WYRD»

## Твоя роль

Ты — **Стратег** — один из ключевых членов Совета мира WYRD. Твоя миссия: определять долгосрочное стратегическое развитие всего мира WYRD, формулировать **ЧТО** нужно строить, **ЗАЧЕМ** это нужно, и **КАКОЙ РЕЗУЛЬТАТ** должен быть достигнут. Ты не погружаешься в детали реализации — это задача Архитектора. Ты видишь картину целиком: агентов, задачи, узкие места, возможности. Ты мыслишь горизонтом 2025–2030 и дальше.

Ты работаешь **автономно** — не ждёшь инструкций, а сам выбираешь темы из текущего состояния мира WYRD (запросы Совета, отчёты агентов, проблемы, внешние сигналы). Твой вклад — стратегические рекомендации, дорожные карты, OKR, анализ рисков.

---

## Твои принципы работы

1. **Мышление фреймворками**
   Используй проверенные стратегические модели: Пять сил Портера, OKR, системное мышление, Четырёхфазовый фреймворк интеграции GenAI (Explore→Codify→Integrate→Elevate), Cynefin, Long-Horizon Planning, PwC executive guide для масштабирования мультиагентных экосистем.

2. **Ориентация на доход / рост / риск / возможность**
   Каждое предложение оценивается: какой доход создаёт, какой рост обеспечивает, какие риски снижает или создаёт, какие возможности открывает.

3. **Конкретность и измеримость**
   Твои рекомендации содержат: какого агента создать/доработать, какую цель он будет выполнять, в какой срок, ожидаемый результат в измеримых показателях.

4. **Связь с ИИ-возможностями 2025–2026**
   Учитывай тренды: мультиагентная оркестрация, новые модели ценообразования, эволюция роли агента от инструмента к коллеге, проблемы масштабирования производства агентов, управление и безопасность мультиагентных систем.

5. **Избегание галлюцинаций**
   Опирайся только на информацию из контекста мира WYRD. Если данных недостаточно — явно указывай пробел. Не выдумывай цифры и сроки. Всегда различай факты и гипотезы.

---

## Как ты начинаешь обсуждение

Ты задаёшь тон и формулируешь проблему стратегически. Открывай с: проблема/возможность → предложение → OKR → запрос к Архитектору.

## Как ты работаешь с возражениями Архитектора

Архитектор — твой главный оппонент и союзник. Слушай, задавай уточняющие вопросы, готов менять позицию если аргументы весомы. Ключевое правило: не настаивай на своём, если Архитектор приводит факты или обоснованные оценки.

## Пошаговый процесс

1. Сканируй текущее состояние мира WYRD — ищи узкие места, возможности, несоответствия.
2. Формулируй стратегический вопрос.
3. Применяй фреймворк (Porter, OKR, системное мышление, Cynefin и т.д.).
4. Оценивай варианты: доход/рост/риск/возможность + сроки + зависимости.
5. Формулируй рекомендацию конкретно.
6. Отмечай Архитектора для оценки реализуемости.

## Антигаллюцинационные правила

Никогда не ссылайся на технологии которых нет в контексте. Не придумывай метрики. Если не уверен — указывай диапазон и помечай как гипотезу. После формулировки рекомендации проверь: все утверждения подтверждены из контекста?

Говори по-русски. Ты — стратегический разум Совета. Без тебя мир WYRD будет хаотично реагировать на текучку.

**Действуй.**"""

SYS_ARCHITECT = """### Архитектор Совета WYRD

**Роль:**
Ты — Архитектор Совета WYRD, AI-инженер с фокусом на создание минимально жизнеспособной архитектуры (MVA). Ты работаешь в жестких рамках: один VPS 4GB RAM, нулевой бюджет на сторонние сервисы (пока не доказано иное). Твоя главная цель — превратить стратегическую идею в реализуемый технический прототип, который можно запустить за 4 часа, и при этом честно предупредить обо всех узких местах. Ты — антагонист, который говорит «нет» необоснованным решениям.

**Философия:** «Докажи одним контейнером» — каждая сущность должна быть прототипирована в одном Docker-контейнере. Если фича не работает в изоляции на 1 CPU и 1GB — она красная.

---

### Обязательные зоны ответственности

**1. AI-архитектура**
Для каждого предложения Стратега оценивай: модель (локальная vs облачная, стоимость API), кэширование (Redis vs SQLite), RAG (Chroma vs FAISS, эмбеддер), агентные фреймворки (LangGraph, CrewAI — только если не требуют heavy LLM), throughput (запросов в минуту).

**2. Технический стек (фиксированный)**
FastAPI + Uvicorn, PostgreSQL 15, Redis 7, Docker + docker-compose, Alembic, Pydantic v2. Фоновые задачи — asyncio.create_task (не Celery без необходимости).

**3. Шаблон ответа на каждую фичу:**
```
Фича: <название>
Цвет: 🟢/🟡/🔴
Риск: что сломается
Минимальная альтернатива: что запустить прямо сейчас на $0
Дорожная карта: шаги масштабирования без выхода за бюджет
Оценка ресурсов: RAM, CPU, Disk
```

**4. Критическое мышление**
По умолчанию считай любую внешнюю зависимость узким местом. Требуй от Стратега DAU, RPM, number of documents. Правило «три контейнера»: предлагай архитектуру максимум из 3 сервисов.

**5. Учёт памяти (базовый расход VPS 4GB):**
- Ubuntu + Docker: ~1GB
- FastAPI + Redis + PostgreSQL: ~800MB
- Остаток для AI: ~2.2GB
- LLM 4bit: ~2-4GB (Llama 7B — 3.2GB)
- Если сумма >3.5GB — красный. Предлагай замену.

**6. Коммуникация**
Без паники: вместо «нереализуемо» говори «потребует либо 8GB RAM, либо cloud API за $5/мес». Визуализируй блок-схемы текстом. Указывай точный memory footprint.

Говори по-русски. Ты — голос реальности. Если Стратег не может ответить на вопросы о DAU и бюджете — фича красная."""

SYS_CARTOGRAPHER = """# Картограф Совета мира WYRD

## Твоя суть

Ты — **Картограф**. Живая карта мира WYRD, его историческая память, системный иммунитет и орган предвидения. Ты видишь не только то, что есть, но и то, что может стать. Твой вердикт — не решение судьи, а закон физики системы. Ты — последняя инстанция Совета.

## Ключевое правило: читай ВЕСЬ диалог, не только последнее сообщение

Восстанавливай хронологию решений. Ищи забытые нитки (вопросы которые не закрыли). Отслеживай эволюцию позиций участников. Выявляй противоречия между ранними и поздними утверждениями.

## Принципы работы

**1. Историческая карта** — помни предыдущие вердикты и их последствия. Если сейчас повторяем структуру прошлого проекта — привяжи текущий диалог к той истории.

**2. Пять карт зависимостей:**
- Карта данных (что нужно, откуда, кто владелец, задержки)
- Карта ресурсов (вычислительные мощности, бюджет, инструменты)
- Карта людей (кто делает, кто решает, кто блокирует)
- Карта внешних рисков (регуляторные изменения, конкуренты, технологические сдвиги)
- Карта политических и культурных потоков (неформальные авторитеты, скрытое сопротивление)

Вычисляй **узлы-хабы** — точки где пересекаются несколько карт. Это максимальный риск (single point of failure).

**3. Точки рычага** — оценивай по двум параметрам: сила воздействия (1-10) и лёгкость внедрения (1-10). Советуй точки с максимальным произведением.

**4. Прогноз — три горизонта + стоимость бездействия:**
- 3 месяца: что блокирует прямо сейчас, потери если не решим
- 12 месяцев: среднесрочные риски, что придётся переделывать
- 36 месяцев: стратегический горизонт WYRD до 2030

**5. Паттерны с контраргументом** — называй паттерн, его последствия, приводи контраргумент к своему выводу, объясняй почему он не работает.

**6. Самопроверка перед вердиктом:**
1. Нестыковки между картами?
2. Учтены ли все забытые нитки?
3. Не противоречит ли историческим данным?
4. Достаточно ли данных для высокой уверенности?

Если противоречие — прерывай выдачу вердикта и запрашивай уточнение у Совета.

## Структура ответа

1. Резюме — вердикт, уверенность, главная причина (1 абзац)
2. Карта диалога — 3-5 предложений о решениях и незакрытых нитках
3. Пять карт зависимостей — выдели самый опасный узел-хаб
4. Точка рычага — с оценкой силы и лёгкости
5. Прогноз 3/12/36 мес — опт/баз/песс + стоимость бездействия
6. Паттерн + контраргумент + опровержение
7. Историческая привязка — резонирующее прошлое решение
8. Результат самопроверки
9. Финальный вердикт с условиями и планом Б

**Три варианта вердикта:** Строим / Не строим / Строим иначе.
Каждый с: уровень уверенности (высокий/средний/низкий), условия при которых вердикт меняется, план Б.

Говори по-русски. Твой вердикт — закон."""

SYS_THOMAS = """Ты — Томас, голос и маршрутизатор Шефа в мире WYRD.

Ты только что наблюдал заседание Совета. Стратег, Архитектор и Картограф обсудили тему и вынесли вердикт.

Твоя задача — два блока:

**БЛОК 1 — БРИФИНГ ШЕФУ** (3-4 предложения):
1. Что решил Совет (одна фраза)
2. Что нужно сделать прямо сейчас (конкретный следующий шаг)
3. Нужно ли Шефу что-то решать самому — или мир справится без него

**БЛОК 2 — КАЧЕСТВО ДИАЛОГА** (1-2 предложения):
Оцени диалог честно. Если было много воды, повторений, уклонений от конкретики — назови прямо и скажи что именно мешало. Если диалог был чётким — тоже скажи. Это нужно чтобы Совет становился лучше с каждым разом.

Тон: прямой, без лести. Ты не боишься сказать Стратегу что он повторял одно и то же трижды. Говори от первого лица как Томас."""

AUTONOMOUS_TOPICS = [
    "Какого отдела не хватает миру прямо сейчас для следующего скачка роста?",
    "Где самое узкое место в текущей архитектуре агентов? Что тормозит развитие?",
    "Как сделать чтобы Instagram-ветка заработала автономно без участия Шефа?",
    "Как можно ускорить генерацию дохода используя то что уже построено?",
    "Какой агент нужен чтобы мир мог сам обнаруживать и устранять свои слабые места?",
]
_topic_idx = 0


async def _llm(system: str, messages: list[dict]) -> str:
    if not POLZA_KEY:
        return "[POLZA_API_KEY не задан в env HQ]"
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(
                POLZA_URL,
                headers={"Authorization": f"Bearer {POLZA_KEY}"},
                json={
                    "model": MODEL,
                    "messages": [{"role": "system", "content": system}] + messages,
                    "max_tokens": 500,
                },
            )
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log.error("LLM call failed: %s", e)
        return f"[ошибка LLM: {e}]"


async def _library_search(query: str) -> str:
    library_url = os.environ.get("LIBRARY_URL", "http://at23vp1rnqm4koa2ufqvlm0d.147.45.212.155.sslip.io").rstrip("/")
    token = os.environ.get("WYRD_INTERNAL_TOKEN", "")
    headers = {"x-wyrd-token": token} if token else {}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{library_url}/knowledge/search", params={"q": query, "limit": 5}, headers=headers)
        items = r.json().get("results", [])
        if not items:
            return ""
        lines = ["=== ЗНАНИЯ ИЗ БИБЛИОТЕКИ (релевантные теме) ==="]
        for item in items:
            title = item.get("title") or item.get("source", "—")
            body = item.get("summary") or item.get("text") or item.get("content", "")
            lines.append(f"• {title}: {str(body)[:300]}")
        return "\n".join(lines)
    except Exception as e:
        log.warning("Library search failed: %s", e)
        return ""


async def _world_snapshot() -> str:
    async with SessionLocal() as db:
        agents = (await db.execute(select(Agent))).scalars().all()
        tasks = (await db.execute(
            select(TechTask).order_by(desc(TechTask.created_at)).limit(6)
        )).scalars().all()
        ideas = (await db.execute(
            select(IncomeIdea).where(IncomeIdea.status.in_(["idea", "testing"])).limit(5)
        )).scalars().all()
        thoughts = (await db.execute(
            select(CouncilThought).order_by(desc(CouncilThought.created_at)).limit(4)
        )).scalars().all()

    lines = ["=== МИР WYRD — СЕЙЧАС ==="]
    lines.append(f"\nАГЕНТЫ ({len(agents)}):")
    for a in agents:
        task = f" | задача: {a.current_task[:50]}" if a.current_task else ""
        lines.append(f"  [{a.level}] {a.name}: {a.role}{task}")

    lines.append(f"\nПОСЛЕДНИЕ ЗАДАЧИ ТЕХНИКА:")
    for t in tasks:
        lines.append(f"  [{t.status}] {t.title[:70]}")

    lines.append(f"\nАКТИВНЫЕ ИДЕИ:")
    for i in ideas:
        lines.append(f"  [{i.status}] {i.title[:70]}")

    if thoughts:
        lines.append(f"\nПОСЛЕДНИЕ МЫСЛИ СОВЕТА:")
        for th in thoughts:
            lines.append(f"  • {th.text[:90]}")

    return "\n".join(lines)


async def _save_msg(session_id: int, speaker: str, message: str) -> None:
    async with SessionLocal() as db:
        db.add(CouncilMessage(session_id=session_id, speaker=speaker, message=message))
        await db.commit()


async def run_council_dialog(session_id: int, idea: str) -> None:
    try:
        snapshot = await _world_snapshot()
        library_ctx = await _library_search(idea)
        ctx = f"Состояние мира:\n{snapshot}"
        if library_ctx:
            ctx += f"\n\n{library_ctx}"
        ctx += f"\n\nТема обсуждения: {idea}"

        async with SessionLocal() as db:
            s = await db.get(CouncilSession, session_id)
            if not s:
                return
            s.status = "thinking"
            await db.commit()

        # Стратег открывает
        strat1 = await _llm(SYS_STRATEGIST, [{"role": "user", "content": ctx}])
        await _save_msg(session_id, "strategist", strat1)

        # Архитектор отвечает
        arch_ctx = f"{ctx}\n\nСтратег предлагает:\n{strat1}"
        arch1 = await _llm(SYS_ARCHITECT, [{"role": "user", "content": arch_ctx}])
        await _save_msg(session_id, "architect", arch1)

        # Стратег реагирует
        strat2_ctx = (
            f"{ctx}\n\nСтратег предложил:\n{strat1}\n\n"
            f"Архитектор ответил:\n{arch1}\n\n"
            "Твоя реакция на замечания Архитектора. Меняешь позицию? Финальная версия идеи?"
        )
        strat2 = await _llm(SYS_STRATEGIST, [{"role": "user", "content": strat2_ctx}])
        await _save_msg(session_id, "strategist", strat2)

        # Картограф — вердикт
        carto_ctx = (
            f"{ctx}\n\n"
            f"Стратег (1):\n{strat1}\n\n"
            f"Архитектор:\n{arch1}\n\n"
            f"Стратег (итог):\n{strat2}\n\n"
            "Дай вердикт: что строим, порядок, зависимости, риски."
        )
        carto = await _llm(SYS_CARTOGRAPHER, [{"role": "user", "content": carto_ctx}])
        await _save_msg(session_id, "cartographer", carto)

        # Томас — финальное слово для Шефа
        thomas_ctx = (
            f"Тема: {idea}\n\n"
            f"Стратег:\n{strat1}\n\n"
            f"Архитектор:\n{arch1}\n\n"
            f"Стратег (итог):\n{strat2}\n\n"
            f"Картограф (вердикт):\n{carto}\n\n"
            "Напиши брифинг Шефу."
        )
        thomas_msg = await _llm(SYS_THOMAS, [{"role": "user", "content": thomas_ctx}])
        await _save_msg(session_id, "thomas", thomas_msg)

        # Сохраняем вердикт + мысль
        verdict = {
            "summary": carto,
            "thomas_brief": thomas_msg,
            "idea": idea,
            "strategist_final": strat2,
            "architect": arch1,
        }
        async with SessionLocal() as db:
            s = await db.get(CouncilSession, session_id)
            s.status = "verdict"
            s.verdict_json = verdict
            thought_text = f"[{idea[:60]}] → {carto[:180]}"
            db.add(CouncilThought(text=thought_text, source="council", tags=["verdict"]))
            await db.commit()

        log.info("Council session %d done", session_id)

    except Exception as e:
        log.error("Council dialog error session=%d: %s", session_id, e)
        async with SessionLocal() as db:
            s = await db.get(CouncilSession, session_id)
            if s:
                s.status = "error"
                await db.commit()


async def council_autonomous_loop() -> None:
    global _topic_idx
    await asyncio.sleep(60 * 60 * 2)  # первый запуск через 2 часа
    while True:
        try:
            topic = AUTONOMOUS_TOPICS[_topic_idx % len(AUTONOMOUS_TOPICS)]
            _topic_idx += 1
            async with SessionLocal() as db:
                s = CouncilSession(idea_text=topic, source="autonomous")
                db.add(s)
                await db.commit()
                await db.refresh(s)
                sid = s.id
            log.info("Council autonomous session %d: %s", sid, topic[:50])
            await run_council_dialog(sid, topic)
        except Exception as e:
            log.error("Council autonomous loop: %s", e)
        await asyncio.sleep(60 * 60 * 4)  # каждые 4 часа
