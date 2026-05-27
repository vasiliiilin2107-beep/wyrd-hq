"""
Seed script — закладываем базовые флаги карты WYRD.
Запуск: python seed_flags.py [HQ_URL]
"""
import sys
import json
import urllib.request
import urllib.error

HQ = (sys.argv[1] if len(sys.argv) > 1
      else "http://m29g5q65uc0vw0r5zku6pukb.147.45.212.155.sslip.io")

FLAGS = [
    # ─── ANCHORS — навигация, где что живёт ───────────────────────────────
    {
        "title": "Главный вход WYRD",
        "body": "Точка старта каждой сессии Моза. Читать первым.",
        "type": "anchor", "component": "global",
        "anchor": "C:/Users/user/neirocech/НАЧАЛО_РАБОТЫ.md",
        "author": "moz",
    },
    {
        "title": "HQ — код штаба",
        "body": "FastAPI + PostgreSQL + Redis + Qdrant. Управляющий центр мира.",
        "type": "anchor", "component": "hq",
        "anchor": "C:/Users/user/wyrd-hq/",
        "author": "moz",
    },
    {
        "title": "Томас — код агента",
        "body": "Telegram-бот, глаза и уши Шефа. Модули: agent/commands/loops/memory.",
        "type": "anchor", "component": "thomas",
        "anchor": "C:/Users/user/personal-agent/",
        "author": "moz",
    },
    {
        "title": "Студия — код контента",
        "body": "FastAPI контент-студия. Боря, Марк, пайплайн 4o_photo.",
        "type": "anchor", "component": "studio",
        "anchor": "C:/Users/user/content-studio/",
        "author": "moz",
    },
    {
        "title": "Библиотека — код знаний",
        "body": "WYRD Library. Qdrant + RAG-библиотекарь. Личная память Томаса.",
        "type": "anchor", "component": "library",
        "anchor": "C:/Users/user/wyrd-library/",
        "author": "moz",
    },
    {
        "title": "Карантин — код защиты",
        "body": "WYRD Quarantine. Эфемерные Docker-контейнеры, маяк, угрозо-библиотека.",
        "type": "anchor", "component": "quarantine",
        "anchor": "C:/Users/user/wyrd-quarantine/",
        "author": "moz",
    },
    # ─── NOTES — информационные, где брать данные ─────────────────────────
    {
        "title": "Ключи и токены",
        "body": "Все API-ключи, токены, пароли. Читать перед генерацией новых.",
        "type": "note", "component": "global",
        "anchor": "C:/Users/user/content-studio/docs/KEYS.md",
        "author": "moz",
    },
    {
        "title": "Состояние студии",
        "body": "Живой документ студии — текущий прогресс, баги, уровни.",
        "type": "note", "component": "studio",
        "anchor": "C:/Users/user/content-studio/docs/STATE.md",
        "author": "moz",
    },
    {
        "title": "Бриф Томаса",
        "body": "Статичная личность Томаса. Обновлять в конце каждой сессии.",
        "type": "note", "component": "thomas",
        "anchor": "context/THOMAS_BRIEF.md",
        "author": "moz",
    },
    {
        "title": "Роадмап мира",
        "body": "Что строим, в каком порядке, приоритеты. Таблица задач по сессиям.",
        "type": "note", "component": "global",
        "anchor": "C:/Users/user/neirocech/НАЧАЛО_РАБОТЫ.md#что-делаем-дальше",
        "author": "moz",
    },
    # ─── DEPENDENCIES — критические зависимости ───────────────────────────
    {
        "title": "PostgreSQL — основная БД",
        "body": "Хранит: branches, events, notes, tasks, backups, flags. Coolify managed.",
        "type": "dependency", "component": "hq",
        "anchor": "hq.database.postgresql",
        "author": "moz",
    },
    {
        "title": "Redis — шина событий",
        "body": "Pub/sub канал wyrd.events. HQ публикует → Томас подписан.",
        "type": "dependency", "component": "hq",
        "anchor": "hq.redis.wyrd_events",
        "author": "moz",
    },
    {
        "title": "Qdrant — векторная память",
        "body": "Systemd на хосте, порт 6333. Коллекции: wyrd_hq + wyrd_library. Данные в /opt/qdrant/storage.",
        "type": "dependency", "component": "hq",
        "anchor": "hq.qdrant.6333",
        "author": "moz",
    },
    {
        "title": "Coolify — деплой платформа",
        "body": "Автодеплой по git push. UI: 147.45.212.155:8000. Токен в KEYS.md.",
        "type": "dependency", "component": "global",
        "anchor": "infrastructure.coolify",
        "author": "moz",
    },
    # ─── BEACONS — точки наблюдения ───────────────────────────────────────
    {
        "title": "HQ health",
        "body": "Точка мониторинга штаба. Живой — мир работает.",
        "type": "beacon", "component": "hq",
        "anchor": "http://m29g5q65uc0vw0r5zku6pukb.147.45.212.155.sslip.io/health",
        "author": "moz",
    },
    {
        "title": "Томас веб-чат",
        "body": "Веб-интерфейс Томаса. Тест диалога без Telegram.",
        "type": "beacon", "component": "thomas",
        "anchor": "http://nliab2x9c4i45glpqn3mdcy0.147.45.212.155.sslip.io",
        "author": "moz",
    },
    {
        "title": "Library health",
        "body": "Точка мониторинга библиотеки и Qdrant-индекса.",
        "type": "beacon", "component": "library",
        "anchor": "http://at23vp1rnqm4koa2ufqvlm0d.147.45.212.155.sslip.io/health",
        "author": "moz",
    },
    # ─── RISKS — известные риски ──────────────────────────────────────────
    {
        "title": "Лимит размера файлов",
        "body": "py≤500 / js≤400 / html≤300 / css≤600 строк. Нарушение = разбивка потом = трата лимитов.",
        "type": "risk", "component": "global",
        "anchor": "global.code_style.file_limits",
        "author": "moz",
    },
    {
        "title": "Chrome не ходит на IP",
        "body": "147.45.212.155 заблокирован напрямую. Coolify — только через API по SSH.",
        "type": "risk", "component": "global",
        "anchor": "infrastructure.network.ip_block",
        "author": "moz",
    },
]


def post_flag(flag: dict) -> dict:
    data = json.dumps(flag).encode()
    req = urllib.request.Request(
        f"{HQ}/flags",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def main():
    print(f"Сеем {len(FLAGS)} флагов в {HQ}\n")
    ok = 0
    for f in FLAGS:
        try:
            result = post_flag(f)
            icon = {"anchor": "⚓", "note": "📌", "dependency": "🔗",
                    "beacon": "📡", "risk": "⚠️"}.get(f["type"], "🚩")
            print(f"  {icon} [{result['id']:>3}] {f['title']}")
            ok += 1
        except Exception as e:
            print(f"  ❌ {f['title']}: {e}")
    print(f"\n✅ Готово: {ok}/{len(FLAGS)} флагов на карте")


if __name__ == "__main__":
    main()
