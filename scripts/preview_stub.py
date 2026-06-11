"""Локальный предпросмотр HQ-статики с моками /bs/* — без PG/Redis/Qdrant.
Запуск: py scripts/preview_stub.py  →  http://127.0.0.1:8123
Остальные API отвечают 404 — комнаты кроме Book Studio покажут error-блоки, это норма.
"""
import json
import re
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "app" / "static"
PORT = 8123

BOOKS = [
    {"slug": "tolstyak", "title": "Толстяк на пути бессмертия", "genre": "xianxia_comedy",
     "chapters_total": 2, "chapters_published": 1, "avg_score": 7.0,
     "rulate_url": "https://tl.rulate.ru/book/123"},
    {"slug": "arhitektor_dush", "title": "Сломанная печать: Архитектор душ", "genre": "xianxia_comedy",
     "chapters_total": 0, "chapters_published": 0, "avg_score": 0, "rulate_url": ""},
    {"slug": "korol_bez_trona", "title": "Король без трона", "genre": "action",
     "chapters_total": 0, "chapters_published": 0, "avg_score": 0, "rulate_url": ""},
]

IDEAS = [
    {"title": "Сломанная печать: Архитектор душ", "genre": "xianxia_comedy",
     "hook": "Некромант проектирует души как чертежи — но его собственная собрана с браком.",
     "why_it_works": "Свежая механика + юмор"},
    {"title": "Король без трона: Право на забвение", "genre": "action",
     "hook": "Император потерял память и трон, но империя помнит его слишком хорошо.",
     "why_it_works": "Интрига с первой главы"},
    {"title": "Не флиртуй с системой!", "genre": "romance_fantasy",
     "hook": "Система выдаёт квесты на соблазнение, героиня хочет только спокойно жить.",
     "why_it_works": "Романтика + комедия, топ на Rulate"},
]

CHAPTERS = [
    {"number": 1, "title": "Глава 1 — Пробуждение обжоры", "score": 7.0, "published": True},
    {"number": 2, "title": "Глава 2 — Система считает калории", "score": 7.4, "published": False},
]

_FN = ["открытие", "конфликт", "поворот", "пик", "развязка"]
ARC = {
    "arc_name": "Арка 1 — Пробуждение обжоры",
    "arc_summary": "Толстяк Лю Фэн узнаёт, что его дух-зверь — собственный аппетит.",
    "chapter_goals": [
        {"number": n, "goal": f"Цель главы {n}: продвинуть Лю Фэна к турниру секты.",
         "arc_function": _FN[(n - 1) % len(_FN)]}
        for n in range(1, 21)
    ],
}

GET_ROUTES = [
    (r"^/bs/stats$", lambda m: {
        "books": BOOKS,
        "total_chapters": sum(b["chapters_total"] for b in BOOKS),
        "total_published": sum(b["chapters_published"] for b in BOOKS),
    }),
    (r"^/bs/analyst/ideas$", lambda m: IDEAS),
    (r"^/bs/books/[^/]+/chapters$", lambda m: CHAPTERS),
    (r"^/bs/books/[^/]+/chapters/(\d+)$", lambda m: {
        **CHAPTERS[0], "content": "Лю Фэн проснулся от урчания в животе.\n\nСистема молчала." }),
    (r"^/bs/books/[^/]+/arc$", lambda m: ARC),
    (r"^/bs/books/[^/]+/conductor$", lambda m: {
        "directives": ["Усилить клиффхэнгеры: главы 3-5", "Больше юмора в диалогах"],
        "summary": "Темп хороший, юмора мало."}),
    (r"^/bs/books/[^/]+/panels$", lambda m: {
        "panels": {"1": {"aggregate": {"avg_score": 7.2, "would_continue_pct": 83}}}}),
    (r"^/bs/books/[^/]+/rulate_metrics$", lambda m: {"views": 1234, "bookmarks": 56, "rating": 4.6}),
]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(STATIC), **kw)

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            self.path = "/hq.html"
            return super().do_GET()
        for pattern, fn in GET_ROUTES:
            m = re.match(pattern, path)
            if m:
                return self._json(fn(m))
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/bs/"):
            return self._json({"ok": True, "queued_chapter": 3, "message": "mock"})
        return self._json({"ok": False}, 404)

    def log_message(self, fmt, *args):
        pass  # тихий режим


if __name__ == "__main__":
    print(f"HQ preview stub: http://127.0.0.1:{PORT} (static: {STATIC})")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
