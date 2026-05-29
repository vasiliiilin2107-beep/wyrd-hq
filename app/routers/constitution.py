from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import Constitution

router = APIRouter(prefix="/constitution", tags=["constitution"])

DEFAULT_TEXT = """# КОНСТИТУЦИЯ МИРА WYRD

## Три закона мира (нарушать нельзя)

### Закон 1 — Штаб управляет, ветки выполняют
Штаб — единственный центр власти. Он знает всех и всем раздаёт задачи.
Ни одна ветка не управляет другой. Студия не командует аналитикой. Аналитика не лезет в студию.
Каждый делает только своё.

### Закон 2 — Разделение функций
Каждая ветка — один функционал, и только он:
- **Штаб** → управляет, координирует, принимает решения
- **Томас** → следит за всем миром, докладывает Шефу, не спит
- **Студия** → генерирует контент. Больше ничего
- **Библиотека** → хранит знания, отвечает на вопросы
- **Аналитика** → считает цифры, строит отчёты
- **Бухгалтерия** → бюджеты, расходы, деньги

Появится новая ветка → она тоже делает одно своё дело.

### Закон 3 — Мир помнит
Каждое важное событие в любой ветке — уходит в память штаба.
Штаб не забывает. Именно из этой памяти мир учится и растёт.
Без памяти — мир сбрасывается в ноль каждую сессию. Это смерть.

---

## Иерархия мира

```
             ШЕФ (Вася)
                │
            ТОМАС (глаза и уши)
                │
    ╔═══════════╩═══════════╗
    ║         ШТАБ          ║  ← единственный управляющий центр
    ║   PostgreSQL + Redis  ║
    ║   FastAPI + Память    ║
    ╚═══════════╦═══════════╝
                │ (шина событий — ветки не говорят напрямую)
    ┌───────────┼───────────┐
    ▼           ▼           ▼
  СТУДИЯ   БИБЛИОТЕКА  АНАЛИТИКА  ... [любая новая ветка]
```
"""


class ConstitutionIn(BaseModel):
    text: str


async def _get_or_create(session: AsyncSession) -> Constitution:
    rec = await session.get(Constitution, 1)
    if not rec:
        rec = Constitution(id=1, text=DEFAULT_TEXT)
        session.add(rec)
        await session.commit()
        await session.refresh(rec)
    return rec


@router.get("")
async def get_constitution(session: AsyncSession = Depends(get_session)):
    rec = await _get_or_create(session)
    return {
        "text": rec.text,
        "updated_at": rec.updated_at.isoformat() if rec.updated_at else None,
    }


@router.put("")
async def save_constitution(body: ConstitutionIn, session: AsyncSession = Depends(get_session)):
    rec = await _get_or_create(session)
    rec.text = body.text
    rec.updated_at = datetime.utcnow()
    await session.commit()
    return {"ok": True, "updated_at": rec.updated_at.isoformat()}
