import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import engine, Base, SessionLocal
from .redis_client import init_redis, close_redis
from .qdrant_store import init_qdrant, close_qdrant
from .routers.civilization import seed_agents
from .routers.education import load_all_dna
from .routers import branches, events, memory, ws, notes, tasks, backups, flags, techtasks, income, tokens, lessons, thomas_proxy, library_proxy, book_studio_proxy, constitution, civilization, council, education, world_docs, build, analytics, ideas_dept, projects_dept, babla, butler, butler_tts, dispatcher_proxy, hq_world, scribe_proxy, agent_log, preview_router
from .routers.avito_auth import router as avito_auth_router
from .council_agent import council_autonomous_loop
from .foreman_agent import foreman_loop
from .audit_agent import audit_loop, router as audit_router
from .analytics_agent import analytics_loop, run_analytics_check
from .idea_agent import idea_loop, run_idea_check
from .project_agent import project_loop, run_project_check
from .babla_agent import babla_loop, run_babla_check
from .treasurer_agent import treasurer_loop, run_treasurer_check
from .professor_agent import professor_loop, run_professor_check
from .template_agent import template_loop
from .library_agent import library_loop
from .watcher_agent import watcher_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

START_TIME = datetime.utcnow()
STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def _seed_clients(session) -> None:
    """Засев реестра клиентов ПРАВДОЙ — идемпотентно (только если пусто)."""
    from sqlalchemy import select, func as _f
    from .models import Client
    if (await session.execute(select(_f.count()).select_from(Client))).scalar():
        return
    seeds = [
        Client(name="Павел", business="Уютный Берег — посуточная аренда домика (Тюмень)",
               pays="15000₽/мес + 15000₽ за сайт+настройку (разово)", status="активен",
               channel="Яндекс.Директ + сайт uytbereg72 + бот @uytbereg72_bot",
               notes="ЕДИНСТВЕННЫЙ платящий клиент мира. НЕ выдумывать с него доп-плату (200₽/лид и пр.) — "
                     "он уже платит. Рост = УДЕРЖАТЬ его + найти ВТОРОГО такого на 15к, а не доить одного."),
        Client(name="Юля", business="Wooden House — домик у реки (аренда)",
               pays="0₽", status="не платит",
               channel="сайт wooden-house72 + бот @Wooden_house72_bot",
               notes="Пользуется инструментами, не платит. НЕ источник дохода."),
        Client(name="Саня", business="Окна/остекление (Тюмень)",
               pays="0₽", status="пауза (сезон)",
               channel="лендинг остекления",
               notes="Встал из-за сезонности. Потенциальный при возврате сезона, сейчас 0₽."),
    ]
    for c in seeds:
        session.add(c)
    await session.commit()


async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # лёгкая миграция build_cards под раздел самоапгрейда (идемпотентно)
        from sqlalchemy import text
        await conn.execute(text(
            "ALTER TABLE build_cards ADD COLUMN IF NOT EXISTS kind VARCHAR(30) DEFAULT 'council'"))
        await conn.execute(text(
            "ALTER TABLE build_cards ADD COLUMN IF NOT EXISTS agent_name VARCHAR(100)"))
        await conn.execute(text(
            "ALTER TABLE build_cards ALTER COLUMN session_id DROP NOT NULL"))
    await init_redis()
    await init_qdrant()
    async with SessionLocal() as session:
        await seed_agents(session)
    # Реестр клиентов — ПРАВДА, идемпотентно, в своей сессии, не роняет старт
    try:
        from sqlalchemy import select as _sel, func as _fn
        from .models import Client as _Client
        async with SessionLocal() as s2:
            if not (await s2.execute(_sel(_fn.count()).select_from(_Client))).scalar():
                s2.add_all([
                    _Client(name="Павел", business="Уютный Берег — посуточная аренда домика (Тюмень)",
                            pays="15000₽/мес + 15000₽ сайт (разово)", status="активен",
                            channel="Директ + сайт uytbereg72 + бот @uytbereg72_bot",
                            notes="ЕДИНСТВЕННЫЙ платящий. НЕ выдумывать доп-плату (200₽/лид) — он уже платит. "
                                  "Рост = удержать + найти ВТОРОГО как Павел на 15к, не доить одного."),
                    _Client(name="Юля", business="Wooden House — домик у реки (аренда)", pays="0₽",
                            status="не платит", channel="сайт wooden-house72 + бот",
                            notes="Пользуется, не платит. Не источник дохода."),
                    _Client(name="Саня", business="Окна/остекление (Тюмень)", pays="0₽",
                            status="пауза (сезон)", channel="лендинг остекления",
                            notes="Встал по сезону, сейчас 0₽, потенциальный при возврате."),
                ])
                await s2.commit()
    except Exception as e:
        logging.getLogger(__name__).warning("seed_clients skip: %s", e)
    # КАРТА ФРОНТИРА — измеренная правда (Rulate 25 жанров), идемпотентно, не роняет старт
    try:
        from sqlalchemy import select as _sf, func as _ff
        from .models import Frontier as _Fr
        async with SessionLocal() as s3:
            if not (await s3.execute(_sf(_ff.count()).select_from(_Fr))).scalar():
                # покрытие: сянься=Толстяк, романтика=Не флиртуй, боевик=Сломанный герб
                _cover = {"Сянься": "tolstyak", "Романтика": "ne_flirtuy_s_sistemoy",
                          "Боевик": "slomannyy_gerb_arhitektor_vozmezdiya"}
                _hot = {"Литрпг", "Сянься", "Боевик", "Городское фэнтези", "Гаремник",
                        "Постапокалиптика", "Героическое фэнтези"}
                _genres = ["Боевик", "Боевые искусства", "История", "Детектив", "Драма", "Комедия",
                           "Мистика", "Повседневность", "Постапокалиптика", "Приключения", "Психология",
                           "Романтика", "Сверхъестественное", "Научная фантастика", "Сюаньхуань",
                           "Героическое фэнтези", "Фэнтези", "Фантастика", "Школа", "Этти", "Гаремник",
                           "Литрпг", "Городское фэнтези", "Сянься", "Фанфик"]
                for g in _genres:
                    s3.add(_Fr(platform="rulate", genre=g, rail_built=True, lang="ru",
                               covered=g in _cover, book_slug=_cover.get(g),
                               demand="высокий (рынок)" if g in _hot else "не измерен",
                               notes="Rulate раздел «Авторские» (cat_id=18)"))
                # площадки без рельса — вся площадка пустая, нужен публикатор-рельс
                _plat = [("author_today", "ru"), ("litnet", "ru"), ("litres", "ru"), ("ridero", "ru"),
                         ("bookmate", "ru"), ("ficbook", "ru"), ("litmarket", "ru"),
                         ("royal_road", "en"), ("webnovel", "en"), ("scribblehub", "en"),
                         ("wattpad", "en"), ("amazon_kdp", "en"), ("naver", "ko")]
                for name, lang in _plat:
                    s3.add(_Fr(platform=name, genre="— (вся площадка)", rail_built=False, lang=lang,
                               notes="рельс-публикатор не построен — весь каталог открыт"))
                await s3.commit()
    except Exception as e:
        logging.getLogger(__name__).warning("seed_frontier skip: %s", e)
    await load_all_dna()
    asyncio.create_task(council_autonomous_loop())
    asyncio.create_task(foreman_loop())
    asyncio.create_task(audit_loop())
    asyncio.create_task(analytics_loop())
    asyncio.create_task(idea_loop())
    asyncio.create_task(project_loop())
    asyncio.create_task(babla_loop())
    asyncio.create_task(treasurer_loop())
    asyncio.create_task(professor_loop())
    asyncio.create_task(template_loop())
    asyncio.create_task(library_loop())
    asyncio.create_task(watcher_loop())
    yield
    await close_qdrant()
    await close_redis()


app = FastAPI(title="WYRD HQ", version="0.3.0", lifespan=lifespan)

app.include_router(branches.router)
app.include_router(events.router)
app.include_router(memory.router)
app.include_router(ws.router)
app.include_router(notes.router)
app.include_router(tasks.router)
app.include_router(backups.router)
app.include_router(flags.router)
app.include_router(techtasks.router)
app.include_router(income.router)
app.include_router(tokens.router)
app.include_router(lessons.router)
app.include_router(thomas_proxy.router)
app.include_router(library_proxy.router)
app.include_router(book_studio_proxy.router)
app.include_router(constitution.router)
app.include_router(civilization.router)
app.include_router(council.router)
app.include_router(education.router)
app.include_router(world_docs.router)
app.include_router(build.router)
from .routers import treasury
app.include_router(treasury.router)
from .routers import frontier
app.include_router(frontier.router)
app.include_router(audit_router)
app.include_router(analytics.router)
app.include_router(ideas_dept.router)
app.include_router(projects_dept.router)
app.include_router(babla.router)
app.include_router(dispatcher_proxy.router)
app.include_router(butler.router)
app.include_router(butler_tts.router)
app.include_router(hq_world.router)
app.include_router(scribe_proxy.router)
app.include_router(agent_log.router)
app.include_router(preview_router.router)
app.include_router(avito_auth_router)

if (STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")
if (STATIC_DIR / "world").exists():
    app.mount("/world", StaticFiles(directory=str(STATIC_DIR / "world")), name="world")
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _html(name: str) -> FileResponse:
    return FileResponse(
        str(STATIC_DIR / name),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.get("/", include_in_schema=False)
def root():
    if (STATIC_DIR / "index.html").exists():
        return _html("index.html")
    return {"message": "WYRD HQ v0.3.0 — мир строится"}


@app.get("/hq", include_in_schema=False)
def hq_page():
    return _html("hq.html")


@app.get("/thomas", include_in_schema=False)
def thomas_page():
    return _html("thomas.html")


@app.get("/studio", include_in_schema=False)
def studio_page():
    return _html("studio.html")


@app.get("/pulse", include_in_schema=False)
def pulse_page():
    return _html("pulse.html")


@app.get("/kazna", include_in_schema=False)
def kazna_page():
    return _html("kazna.html")


@app.get("/agent/{name}", include_in_schema=False)
def agent_passport_page(name: str):
    return _html("agent_passport.html")


@app.get("/manifest.json", include_in_schema=False)
def manifest():
    return FileResponse(str(STATIC_DIR / "manifest.json"), media_type="application/manifest+json")


_TRIGGERS = {
    "analytics": run_analytics_check,
    "ideas":     run_idea_check,
    "projects":  run_project_check,
    "babla":     run_babla_check,
    "treasurer": run_treasurer_check,
    "professor": run_professor_check,
}

@app.post("/trigger/all", tags=["trigger"])
async def trigger_all():
    for fn in _TRIGGERS.values():
        asyncio.create_task(fn())
    return {"ok": True, "launched": list(_TRIGGERS)}

@app.post("/trigger/{agent}", tags=["trigger"])
async def trigger_agent(agent: str):
    fn = _TRIGGERS.get(agent)
    if not fn:
        from fastapi import HTTPException
        raise HTTPException(404, f"Триггер '{agent}' не найден. Доступны: {list(_TRIGGERS)}")
    asyncio.create_task(fn())
    return {"ok": True, "agent": agent, "status": "запущен"}

@app.get("/health")
def health():
    uptime = (datetime.utcnow() - START_TIME).seconds
    return {
        "status": "ok",
        "service": "wyrd-hq",
        "version": "0.3.0",
        "uptime_seconds": uptime,
        "timestamp": datetime.utcnow().isoformat(),
    }
