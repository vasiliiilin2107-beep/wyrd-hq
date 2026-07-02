"""Ф1 арх.v2 — РАСКЛАДКА ЦЕЛИ ВНИЗ (ТЗ_СОВЕТ_ПОТОК_ВНИЗ.md).

Вход мира = ЦЕЛЬ (не идея). Цель течёт ВНИЗ по иерархии — каждый слой раскладывает
её на свой уровень и передаёт ниже. Совет здесь НЕ автор и НЕ судья идей — он визирует
стык. Цепочка ОБЯЗАНА упереться в исполнение: либо агент катает сам (модель Book Studio),
либо один чистый спек реактора для стройки (Шеф+Моз). Третьего — «карточка человеку
как-нибудь» — не существует. Дыра в штате → найм-ТЗ (Профессор).
"""
import json
import logging

from .council_agent import _llm, _get_clients_brief

log = logging.getLogger(__name__)

DECOMP_MODEL = "anthropic/claude-sonnet-4.6"  # раскладка цели — точечно качеством, не объёмом

SYS_DECOMPOSE = """Ты — иерархия WYRD, раскладывающая ЦЕЛЬ Шефа вниз по слоям. Не фантазёр,
не генератор идей. Тебе дали ЦЕЛЬ — разложи её сверху вниз, каждый слой на свой уровень:

  Стратег    → направление: как цель ложится на мир, что она двигает.
  Картограф  → сверка с ПРАВДОЙ: что под это УЖЕ ЕСТЬ (активы/рельсы/клиенты), где ДЫРА.
  Архитектор → реактор: какие модули/рельсы нужны (конкретно, из того что есть или рядом).
  Бригадир   → рабочие единицы: 2-4 конкретных шага исполнения.
  Профессор  → кто катает: хватает штата ИЛИ нужен новый агент (роль + зачем).

ЖЕЛЕЗНЫЙ ЗАКОН ТЕРМИНАЛА: цепочка кончается ровно одним из двух —
  • "agent_runs"    — существующие агенты катают это сами (напр. Book Studio пишет книги);
  • "reactor_spec"  — нужен код/рельс, который построят Шеф+Моз: дай ЧИСТЫЙ спек (5 полей).
«Постройте как-нибудь» / «ещё подумать» — ЗАПРЕЩЕНО. Если упёрлось в отсутствующего
работника — это дыра, заполни поле hole (роль + зачем), терминал всё равно reactor_spec.

Без воды и выдуманных цифр. Опирайся на правду о клиентах/активах. Отвечай ТОЛЬКО JSON."""


async def decompose_goal(goal_text: str, source: str = "chief") -> dict:
    """Раскладывает цель вниз → структурная декомпозиция с терминалом.
    Возвращает dict со слоями, terminal, reactor_spec (если нужен), hole."""
    clients = await _get_clients_brief()
    prompt = f"""ЦЕЛЬ (вход мира, источник: {source}):
«{goal_text}»

{clients}

Разложи эту ЦЕЛЬ вниз по слоям иерархии и упри в исполнение.

JSON:
{{
  "strateg": "направление — 1-2 предложения",
  "kartograf": "что ЕСТЬ под цель / где ДЫРА — по правде",
  "architect": "реактор: модули/рельсы — конкретно",
  "brigadir": ["шаг 1", "шаг 2", "шаг 3"],
  "professor": "штат хватает | нужен агент: <роль> для <зачем>",
  "terminal": "agent_runs | reactor_spec",
  "reactor_spec": {{
    "kto": "что за модуль/рельс/агент строим",
    "zachem": "зачем — какую работу закрывает",
    "zakryvaet": "какую цель/рынок открывает",
    "zavisit_ot": "от чего зависит (существующие рельсы/API)",
    "pervyy_shag": "конкретное первое действие стройки"
  }},
  "hole": "пусто ИЛИ 'нужен агент: <роль> — <зачем>'",
  "verdict": "одна фраза — чем кончается цепочка"
}}
Если terminal=agent_runs — reactor_spec можно оставить пустыми строками."""
    raw = await _llm(SYS_DECOMPOSE, [{"role": "user", "content": prompt}],
                     max_tokens=1600, model=DECOMP_MODEL, caller="goal_decompose")
    d = _parse(raw)
    if not d:
        return {"terminal": "", "verdict": "раскладка не удалась (LLM пусто)", "raw": raw[:400]}
    d.setdefault("terminal", "reactor_spec")
    if d["terminal"] not in ("agent_runs", "reactor_spec"):
        d["terminal"] = "reactor_spec"
    log.info("[ЦЕЛЬ→РАСКЛАДКА] terminal=%s hole=%s verdict=%s",
             d.get("terminal"), bool((d.get("hole") or "").strip()), d.get("verdict", "")[:60])
    return d


def _parse(text: str) -> dict:
    if not text:
        return {}
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.startswith("json"):
            t = t[4:]
    s, e = t.find("{"), t.rfind("}")
    if s < 0 or e <= s:
        return {}
    for cand in (t[s:e + 1],):
        try:
            r = json.loads(cand)
            return r if isinstance(r, dict) else {}
        except Exception:
            pass
    return {}


def reactor_spec_text(d: dict) -> str:
    """Спек реактора → чистый текст ТЗ (шаблон «читается за 5 секунд»)."""
    rs = d.get("reactor_spec") or {}
    lines = [
        f"КТО:        {rs.get('kto','')}",
        f"ЗАЧЕМ:      {rs.get('zachem','')}",
        f"ЗАКРЫВАЕТ:  {rs.get('zakryvaet','')}",
        f"ЗАВИСИТ ОТ: {rs.get('zavisit_ot','')}",
        f"ПЕРВЫЙ ШАГ: {rs.get('pervyy_shag','')}",
    ]
    if (d.get("hole") or "").strip():
        lines.append(f"ДЫРА В ШТАТЕ: {d['hole']}")
    return "\n".join(lines)
