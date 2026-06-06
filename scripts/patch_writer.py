"""
Патчит writer.py и scriptwriter.py — добавляет LIBRARY_LESSONS в SYSTEM промпты.
"""
import re

# ─── constants.py — добавляем LIBRARY_LESSONS ─────────────────────────────

LIBRARY_LESSONS_BLOCK = '''

# =============================================================================
# УРОКИ ИЗ БИБЛИОТЕКИ WYRD (собрано читателями, инжектировано 04.06.2026)
# =============================================================================
LIBRARY_LESSONS = """
━━━ ФОРМУЛА ГЛАВЫ (законы, не рекомендации) ━━━

СТРУКТУРА — проверено на топ xianxia/web-novel:
  10% → ХВАТ: мини-клиффхэнгер или прямое продолжение
        НЕ: "Ли Цзюнь был юношей..."  ДА: "Уведомление мигнуло перед носом."
  60% → МЯСО: культивация / конфликт / мир / монолог ГГ
        Допаминовый удар каждые 500-1000 слов:
        победа, навык, находка, провокация, комический абсурд
  30% → КЛИФФХЭНГЕР: обрыв на действии, вопросе или иронии
        ЗАПРЕЩЕНО: "И так он понял..." / "Всё изменилось..."

ДРОПАУТ — данные с Royal Road / Rulate:
  Гл.1:   40-60% уходят если нет крючка в первых 3 абзацах
  Гл.2-3: 20-30% уходят — проверяют была ли гл.1 случайной
  Гл.4-10: 10-15%/гл — стоит сюжету встать → смерть
  Гл.10+: 2-5%/гл — преданные, нужна эмоциональная инвестиция
  ЗАКОН: 1 глава = 1 закрытый вопрос + 1 новый открытый вопрос

ЮМОР В СЯНЬСЯ:
  Абсурдную ситуацию описываешь с МЁРТВОЙ СЕРЬЁЗНОСТЬЮ
  ГГ: прагматичен (цена / вероятность / условие) — не эмоционален
  Комедия = расстояние между ожидаемым и случившимся
  НЕ объясняй шутку — если объяснил, убей абзац

НЕПРЕРЫВНОСТЬ — отслеживай или потеряешь читателей:
  Имена второстепенных, локации, уровни культивации, предметы у ГГ
  Долги и договоры — ГГ помнит ВСЁ (это источник будущих сцен)
  ЧИТАТЕЛЬ ПОМНИТ ВСЁ — автор обязан тоже

СЦЕНА ЖИВЁТ ТОЛЬКО ЕСЛИ:
  ✓ Двигает характер (он меняется или мы узнаём новое)
  ✓ Двигает сюжет (что-то случается)
  ✗ Только передаёт инфо → вырезать или переписать через действие
"""
'''

WRITER_SYSTEM_INJECT = """
ЗАКОНЫ ИЗ АНАЛИЗА ТОПОВЫХ РАНОБЭ (обязательны):
- Допаминовый удар каждые 500-1000 слов: маленькая победа, новый навык, поворот
- Дропаут гл.1 = 40-60% — первые 3 абзаца решают всё
- Каждая глава = 1 закрытый вопрос + 1 новый открытый
- ЮМОР: абсурд через мертвую серьёзность, не через объяснение
- НЕПРЕРЫВНОСТЬ: имена, локации, уровни культивации не меняются без причины
"""

import sys

constants_path = "/app/core/constants.py"
writer_path = "/app/agents/writer.py"
scriptwriter_path = "/app/agents/scriptwriter.py"

# 1. Патчим constants.py
with open(constants_path, "r", encoding="utf-8") as f:
    c = f.read()

if "LIBRARY_LESSONS" not in c:
    c = c.rstrip() + "\n" + LIBRARY_LESSONS_BLOCK + "\n"
    with open(constants_path, "w", encoding="utf-8") as f:
        f.write(c)
    print("constants.py: LIBRARY_LESSONS added")
else:
    print("constants.py: LIBRARY_LESSONS already exists")

# 2. Патчим writer.py — добавляем import и inject в SYSTEM
with open(writer_path, "r", encoding="utf-8") as f:
    w = f.read()

# Добавляем import LIBRARY_LESSONS если нет
if "LIBRARY_LESSONS" not in w:
    w = w.replace(
        "from core.constants import WRITING_RULES, SLOP_PATTERNS",
        "from core.constants import WRITING_RULES, SLOP_PATTERNS, LIBRARY_LESSONS"
    )
    # Добавляем в SYSTEM промпт перед ВОЗВРАЩАЕШЬ
    INJECT_BEFORE = "ВОЗВРАЩАЕШЬ: только текст главы."
    if INJECT_BEFORE in w:
        w = w.replace(
            INJECT_BEFORE,
            "{library_lessons}\n\n" + INJECT_BEFORE
        )
        # Добавляем library_lessons в вызов ai_call
        # Найдём место где формируется prompt
        w = w.replace(
            'notes_block = ""\n    if agent_notes:',
            'library_block = LIBRARY_LESSONS\n    notes_block = ""\n    if agent_notes:'
        )
        print("writer.py: LIBRARY_LESSONS injected into SYSTEM and prompt")
    else:
        print("writer.py: INJECT_BEFORE not found, skipping")
else:
    print("writer.py: LIBRARY_LESSONS already injected")

with open(writer_path, "w", encoding="utf-8") as f:
    f.write(w)

# 3. Патчим scriptwriter.py — добавляем в SYSTEM правила
with open(scriptwriter_path, "r", encoding="utf-8") as f:
    s = f.read()

if "LIBRARY_LESSONS" not in s:
    # Найдём конец SYSTEM строки
    if "from core.constants import" in s:
        s = s.replace(
            "from core.constants import",
            "from core.constants import LIBRARY_LESSONS  # noqa\nfrom core.constants import",
            1
        )

    # Добавим в конец SYSTEM промпта блок уроков
    SYSTEM_END_MARKER = 'ВОЗВРАЩАЕШЬ: только JSON'
    if SYSTEM_END_MARKER in s:
        s = s.replace(
            SYSTEM_END_MARKER,
            "ЗАКОНЫ ВОВЛЕЧЁННОСТИ (данные Rulate/Royal Road):\n"
            "- Гл.1: 40-60% дропаут — первые 3 абзаца решают\n"
            "- Каждая сцена плана = 1 закрытый вопрос + 1 новый открытый\n"
            "- Допаминовый удар каждые 500-1000 слов в тексте\n"
            "- ЮМОР: абсурд через мёртвую серьёзность ГГ\n\n"
            + SYSTEM_END_MARKER
        )
        print("scriptwriter.py: retention laws injected")
    else:
        print("scriptwriter.py: ВОЗВРАЩАЕШЬ marker not found")
else:
    print("scriptwriter.py: already patched")

with open(scriptwriter_path, "w", encoding="utf-8") as f:
    f.write(s)

print("All done!")
