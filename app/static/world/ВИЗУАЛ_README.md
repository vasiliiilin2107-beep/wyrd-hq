# WYRD Visual Maps — Техническая записка
> Следующий Моз: читай это перед тем как трогать визуал. 5 минут — и ты в контексте.

---

## Что это и зачем

Три HTML-карты мира WYRD. Живые — частицы летят по нитям в реальном времени.
Шеф должен видеть мир глазами, а не читать код.

**Файлы:**
| Файл | Что показывает |
|------|----------------|
| `WYRD_MAP.html` + `wyrd_connections.js` | Здание с комнатами по этажам. Нити между комнатами. |
| `WYRD_GRID.html` + `wyrd_grid.js` | Квадраты агентов в строгом иерархическом порядке. |
| `WYRD_AGENTS.html` + `wyrd_agents.js` | D3.js force-граф: каждый агент = узел, нити = потоки данных. |

**Навигация** между тремя картами — ссылки вверху каждой страницы.

---

## Как устроены связи (нити)

Каждая нить = массив `LINKS` в JS файле. Структура:
```javascript
{ source: 'room-hq', target: 'room-library', color: '#4a9eff', dur: 2.5 }
// или для агентов:
{ s: 'tomas', t: 'bibliotekar', type: 'knowledge' }
```

**Типы связей и цвета:**
| Тип | Цвет | Смысл |
|-----|------|-------|
| `command` | `#4a9eff` синий | команда сверху вниз |
| `knowledge` | `#4aff88` зелёный | передача знаний |
| `report` | `#ffaa00` оранжевый | отчёт снизу вверх |
| `money` | `#44ff44` зелёный | финансовый поток |
| `content` | `#cc44ff` фиолетовый | контент |

**Частицы** — летят по кривой Безье от source к target. Чем больше `dur` — тем медленнее летит.

---

## Как добавить новую связь

### В WYRD_MAP.html (комнаты):
Открыть `wyrd_connections.js`, добавить в массив `LINKS`:
```javascript
{ from: 'room-hq', to: 'room-analytics', color: '#ffaa00', dur: 3.0, label: 'отчёты' }
```
IDs комнат: `room-hq`, `room-projects`, `room-library`, `room-edu`, `room-analytics`, `room-media`, `room-money`, `room-promo`

### В WYRD_GRID.html (квадраты):
Открыть `wyrd_grid.js`, добавить в массив `LINKS`:
```javascript
{ s: 'strateg', t: 'analitika', type: 'command' }
```
IDs агентов: `shef`, `tomas`, `strateg`, `arhitektor`, `kartograf`, `kaznachey`, `proektniy`, `audit`, `bibliotekar`, `arhivarius`, `pisatel`, `skrayb`, `musorschik`, `hugin`, `chitatel`, `profobr`, `analitika`, `studiya`, `finansy`, `ideynyy`, `reklama`, `tehnik`

### В WYRD_AGENTS.html (граф):
Открыть `wyrd_agents.js`, добавить в массив `LINKS`:
```javascript
{ source: 'kartograf', target: 'analitika', type: 'report' }
```

---

## Как добавить нового агента

1. В `NODES` массив добавить объект:
```javascript
{ id: 'noviy', e: '🆕', n: 'НОВЫЙ', dept: 'hq', d: 'Описание для тултипа' }
```
2. В `POS` (только для GRID) добавить позицию:
```javascript
noviy: [0.60, 0.33]  // [x%, y%] от размера экрана
```
3. Добавить нужные связи в `LINKS`

---

## Деплой

Файлы лежат в `wyrd-hq/app/static/world/`.
FastAPI автоматически отдаёт статику через `StaticFiles`.
После `git push` → Coolify задеплоит → карты живут на сервере постоянно.

**URL после деплоя:**
```
https://m29g5q65uc0vw0r5zku6pukb.147.45.212.155.sslip.io/static/world/WYRD_MAP.html
```

---

## Что делать дальше (план Шефа)

Строим связи **по этажам** — снизу вверх по сложности:
1. Сначала добавить всех агентов каждого отдела в `NODES`
2. Потом прописать связи внутри отдела
3. Потом связи между отделами
4. Потом подключить реальные данные из HQ API (пульс агентов)

**Конечная цель:** нить вспыхивает когда Томас реально идёт в Библиотеку. Не статика — живые данные.

---

*Создано: 31.05.2026 — сессия 74*
