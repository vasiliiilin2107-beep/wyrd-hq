"""КАРТА ФРОНТИРА (архитектура v2).
Мир видит: где мы стоим, где пусто, куда целить. Заземлено на ИЗМЕРЕННЫХ данных
площадок (не предположение). Закрытие ветки на потоке открывает соседние клетки.

- GET /frontier        — карта: сводка + по площадкам + топ-дыры
- GET /frontier/gaps    — дыры для прицела ⑨ спавна (что писать СЛЕДУЮЩИМ)
- POST /frontier/cover  — отметить клетку покрытой (когда книга легла на площадку)
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import Frontier

router = APIRouter(prefix="/frontier", tags=["frontier"])

_DEMAND_RANK = {"высокий": 3, "высокий (рынок)": 3, "средний": 2, "низкий": 1, "не измерен": 0}


def _cell(f: Frontier) -> dict:
    return {
        "id": f.id, "platform": f.platform, "genre": f.genre,
        "rail_built": f.rail_built, "covered": f.covered,
        "book_slug": f.book_slug, "demand": f.demand, "lang": f.lang, "notes": f.notes,
    }


@router.get("")
async def frontier_map(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Frontier))).scalars().all()
    platforms: dict[str, dict] = {}
    for f in rows:
        p = platforms.setdefault(f.platform, {"платформа": f.platform, "рельс": f.rail_built,
                                              "язык": f.lang, "клеток": 0, "покрыто": 0, "жанры_покрыты": []})
        p["клеток"] += 1
        if f.covered:
            p["покрыто"] += 1
            p["жанры_покрыты"].append(f"{f.genre} ({f.book_slug})")

    total, covered = len(rows), sum(1 for f in rows if f.covered)
    rails = sum(1 for p in platforms.values() if p["рельс"])
    # топ-дыры: рельс есть (можно писать СЕЙЧАС), не покрыто, по спросу
    fillable = sorted(
        [f for f in rows if f.rail_built and not f.covered and f.genre != "— (вся площадка)"],
        key=lambda f: -_DEMAND_RANK.get(f.demand, 0),
    )
    return {
        "сводка": {
            "площадок": len(platforms), "рельсов_построено": rails,
            "клеток_всего": total, "покрыто": covered, "пусто": total - covered,
            "вердикт": f"Мир занял {covered} клеток из {total}. Фронтир открыт.",
        },
        "по_площадкам": list(platforms.values()),
        "топ_дыры_писать_сейчас": [_cell(f) for f in fillable[:10]],
        "площадки_без_рельса": [f.platform for f in rows if not f.rail_built and f.genre == "— (вся площадка)"],
    }


@router.get("/gaps")
async def frontier_gaps(session: AsyncSession = Depends(get_session)):
    """Прицел для ⑨ спавна: заполнимые клетки (рельс есть), топ по спросу первым."""
    rows = (await session.execute(
        select(Frontier).where(Frontier.rail_built == True, Frontier.covered == False)
    )).scalars().all()
    cells = [f for f in rows if f.genre != "— (вся площадка)"]
    cells.sort(key=lambda f: -_DEMAND_RANK.get(f.demand, 0))
    return {"писать_следующим": [_cell(f) for f in cells[:15]],
            "подсказка": "⑨ спавн целит в верх списка — пустой жанр на площадке с рельсом, по спросу."}


class CoverIn(BaseModel):
    platform: str
    genre: str
    book_slug: str


@router.post("/cover")
async def frontier_cover(body: CoverIn, session: AsyncSession = Depends(get_session)):
    f = (await session.execute(
        select(Frontier).where(Frontier.platform == body.platform, Frontier.genre == body.genre)
    )).scalars().first()
    if not f:
        f = Frontier(platform=body.platform, genre=body.genre, rail_built=True)
        session.add(f)
    f.covered = True
    f.book_slug = body.book_slug
    await session.commit()
    return {"ok": True, "клетка": f"{body.platform}/{body.genre}", "покрыто": body.book_slug}
