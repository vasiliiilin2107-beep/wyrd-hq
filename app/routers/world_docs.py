from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/api/world", tags=["world"])

DOCS_ROOT = Path(__file__).parent.parent / "static" / "world" / "docs"

DEPARTMENTS = [
    {"id": "HQ",        "name": "Штаб HQ",    "icon": "🏛️", "file": "ОТДЕЛ_HQ.md"},
    {"id": "БИБЛИОТЕКА","name": "Библиотека", "icon": "📚", "file": "ОТДЕЛ_БИБЛИОТЕКА.md"},
]

AGENTS = [
    {"id": "ТОМАС",      "name": "Томас",      "icon": "👁️", "dept": "HQ",         "file": "ПАСПОРТ_ТОМАС.md"},
    {"id": "СТРАТЕГ",    "name": "Стратег",    "icon": "🧭", "dept": "HQ",         "file": "ПАСПОРТ_СТРАТЕГ.md"},
    {"id": "АРХИТЕКТОР", "name": "Архитектор", "icon": "🏗️", "dept": "HQ",         "file": "ПАСПОРТ_АРХИТЕКТОР.md"},
    {"id": "КАРТОГРАФ",  "name": "Картограф",  "icon": "🗺️", "dept": "HQ",         "file": "ПАСПОРТ_КАРТОГРАФ.md"},
    {"id": "КАЗНАЧЕЙ",   "name": "Казначей",   "icon": "💰", "dept": "HQ",         "file": "ПАСПОРТ_КАЗНАЧЕЙ.md"},
]


@router.get("/departments")
async def list_departments():
    result = []
    for d in DEPARTMENTS:
        agents = [a for a in AGENTS if a["dept"] == d["id"]]
        result.append({**d, "agents": [{"id": a["id"], "name": a["name"], "icon": a["icon"]} for a in agents]})
    return {"departments": result}


@router.get("/departments/{dept_id}")
async def get_department(dept_id: str):
    dept = next((d for d in DEPARTMENTS if d["id"] == dept_id), None)
    if not dept:
        raise HTTPException(404, "Department not found")
    path = DOCS_ROOT / "departments" / dept["file"]
    if not path.exists():
        raise HTTPException(404, "File not found")
    return PlainTextResponse(path.read_text(encoding="utf-8"))


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    agent = next((a for a in AGENTS if a["id"] == agent_id), None)
    if not agent:
        raise HTTPException(404, "Agent not found")
    path = DOCS_ROOT / "agents" / agent["file"]
    if not path.exists():
        raise HTTPException(404, "File not found")
    return PlainTextResponse(path.read_text(encoding="utf-8"))
