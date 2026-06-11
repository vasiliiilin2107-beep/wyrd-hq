"""In-memory журнал запусков агентов — живой лог для Офиса.
Без БД: хранит последние 100 запусков, теряется при рестарте (это нормально).
Паттерн: start_run() → append() построчно → finish(). Фронт поллит /agent-log/{run_id}/tail.
"""
import time
import uuid
from collections import OrderedDict

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/agent-log", tags=["agent-log"])

_RUNS: "OrderedDict[str, dict]" = OrderedDict()
_MAX_RUNS = 100


def start_run(agent: str, title: str) -> str:
    run_id = uuid.uuid4().hex[:12]
    _RUNS[run_id] = {
        "agent": agent,
        "title": title,
        "lines": [],
        "done": False,
        "ok": None,
        "started": time.time(),
    }
    while len(_RUNS) > _MAX_RUNS:
        _RUNS.popitem(last=False)
    return run_id


def append(run_id: str, text: str) -> None:
    run = _RUNS.get(run_id)
    if run is None or run["done"]:
        return
    run["lines"].append({"t": round(time.time() - run["started"], 1), "text": text})


def finish(run_id: str, ok: bool) -> None:
    run = _RUNS.get(run_id)
    if run is None:
        return
    run["done"] = True
    run["ok"] = ok


@router.get("/recent")
async def recent_runs(limit: int = 10):
    """Последние запуски — для истории в Офисе."""
    runs = []
    for run_id, run in reversed(_RUNS.items()):
        runs.append({
            "run_id": run_id,
            "agent": run["agent"],
            "title": run["title"],
            "done": run["done"],
            "ok": run["ok"],
            "lines_count": len(run["lines"]),
            "started": run["started"],
        })
        if len(runs) >= limit:
            break
    return {"runs": runs}


@router.get("/{run_id}/tail")
async def tail(run_id: str, since: int = 0):
    """Хвост лога с позиции since. Фронт поллит каждые 1.5 сек до done:true."""
    run = _RUNS.get(run_id)
    if run is None:
        raise HTTPException(404, "Запуск не найден (журнал в памяти — рестарт стирает)")
    return {
        "agent": run["agent"],
        "title": run["title"],
        "lines": run["lines"][since:],
        "next": len(run["lines"]),
        "done": run["done"],
        "ok": run["ok"],
    }
