"""Патч hq.html — новая вкладка Book Studio"""

NEW_TAB = '''      <!-- TAB: BOOKSTUDIO -->
      <div id="tab-bookstudio" class="tab-panel" style="display:none">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;flex-wrap:wrap;gap:8px">
          <div class="section-title" style="margin:0">📖 BOOK STUDIO</div>
          <button class="wmap-refresh" onclick="loadBookStudio()">↻</button>
        </div>
        <div id="bs-stats" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin-bottom:16px"></div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px">
          <div id="bs-lore" style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px"></div>
          <div id="bs-chapters" style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px"></div>
        </div>
        <div id="bs-chapter-text" style="display:none;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:16px;margin-bottom:14px;max-height:420px;overflow-y:auto;white-space:pre-wrap;font-size:.8rem;line-height:1.7;color:var(--text)"></div>
        <div id="bs-scout" style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px"></div>
      </div>'''

NEW_JS = r"""  // ── BOOK STUDIO ──────────────────────────────────────────
  let _bsSlug = null;
  let _bsChapterOpen = null;

  async function loadBookStudio() {
    document.getElementById("bs-stats").innerHTML = '<div style="color:var(--text-dim);font-size:.8rem">Загрузка...</div>';
    try {
      const [statsR, booksR] = await Promise.all([
        fetch("/bs/stats"), fetch("/bs/books")
      ]);
      const stats = await statsR.json();
      const booksData = await booksR.json();
      const books = Array.isArray(booksData) ? booksData : (booksData.books || []);

      document.getElementById("bs-stats").innerHTML = `
        <div style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:12px 14px">
          <div style="font-size:1.5rem;font-weight:800;color:var(--amber)">${stats.total_chapters||0}</div>
          <div style="font-size:.65rem;color:var(--text-dim);margin-top:2px;letter-spacing:.1em">НАПИСАНО</div>
        </div>
        <div style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:12px 14px">
          <div style="font-size:1.5rem;font-weight:800;color:var(--green)">${stats.total_published||0}</div>
          <div style="font-size:.65rem;color:var(--text-dim);margin-top:2px;letter-spacing:.1em">ОПУБЛИКОВАНО</div>
        </div>
        <div style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:12px 14px">
          <div style="font-size:1.5rem;font-weight:800;color:var(--purple)">${books.length}</div>
          <div style="font-size:.65rem;color:var(--text-dim);margin-top:2px;letter-spacing:.1em">КНИГ</div>
        </div>`;

      if (!books.length) {
        document.getElementById("bs-lore").innerHTML = '<div style="color:var(--text-dim)">Нет книг</div>';
        return;
      }

      const b = books[0];
      _bsSlug = b.slug;

      const [detR, chR] = await Promise.all([
        fetch("/bs/books/" + b.slug),
        fetch("/bs/books/" + b.slug + "/chapters")
      ]);
      const det = await detR.json();
      const chData = await chR.json();
      const chapters = Array.isArray(chData) ? chData : (chData.chapters || []);

      // ── ЛЕВО: суть книги ──
      const lore = det.lore || "";
      const bible = det.bible || {};
      const theme = bible.theme || {};

      const arcMatch = lore.match(/## ПЛАН АРК[\s\S]*?(?=\n##|$)/);
      const arcText = arcMatch ? arcMatch[0].replace(/## ПЛАН АРК[^\n]*/, "").trim() : "";

      const heroLines = [];
      const heroMatch = lore.match(/## ГЛАВНЫЙ ГЕРОЙ[^\n]*\n([\s\S]*?)(?=\n## )/);
      if (heroMatch) heroLines.push(...heroMatch[1].split("\n").slice(0,5).filter(Boolean));

      const daoMatch = lore.match(/## МЕХАНИКА ДАО[\s\S]*?(?=\n## )/);
      const daoText = daoMatch ? daoMatch[0].replace(/## МЕХАНИКА ДАО[^\n]*\n/, "").split("\n").slice(0,5).join("\n").trim() : "";

      const ruUrl = det.rulate_book_id ? "https://tl.rulate.ru/book/" + det.rulate_book_id : (b.rulate_url || "");

      document.getElementById("bs-lore").innerHTML = `
        <div style="font-size:.7rem;color:var(--text-dim);letter-spacing:.1em;margin-bottom:10px">📚 ${b.title||det.title}</div>
        ${theme.statement ? `<div style="margin-bottom:10px">
          <div style="font-size:.65rem;color:var(--amber);font-weight:700;letter-spacing:.1em;margin-bottom:3px">ТЕМА</div>
          <div style="font-size:.78rem;color:var(--text);line-height:1.6">${theme.statement}</div>
        </div>` : ""}
        ${heroLines.length ? `<div style="margin-bottom:10px">
          <div style="font-size:.65rem;color:var(--purple);font-weight:700;letter-spacing:.1em;margin-bottom:3px">ГЕРОЙ</div>
          <div style="font-size:.75rem;color:var(--text);line-height:1.6;white-space:pre-line">${heroLines.join("\n")}</div>
        </div>` : ""}
        ${daoText ? `<div style="margin-bottom:10px">
          <div style="font-size:.65rem;color:var(--green);font-weight:700;letter-spacing:.1em;margin-bottom:3px">МЕХАНИКА ДАО</div>
          <div style="font-size:.75rem;color:var(--text);line-height:1.6;white-space:pre-line">${daoText.substring(0,280)}</div>
        </div>` : ""}
        ${arcText ? `<div style="margin-bottom:12px">
          <div style="font-size:.65rem;color:#60a5fa;font-weight:700;letter-spacing:.1em;margin-bottom:3px">ПЛАН АРОК</div>
          <div style="font-size:.75rem;color:var(--text);line-height:1.7;white-space:pre-line">${arcText}</div>
        </div>` : ""}
        <div style="padding-top:10px;border-top:1px solid var(--border);display:flex;gap:8px;flex-wrap:wrap">
          <button class="wyrd-btn wyrd-btn-sm" onclick="bsGenerate('${b.slug}')">＋ Глава</button>
          ${ruUrl ? `<a href="${ruUrl}" target="_blank" class="wyrd-btn wyrd-btn-sm wyrd-btn-ghost">Rulate ↗</a>` : ""}
        </div>`;

      // ── ПРАВО: список глав ──
      const sorted = [...chapters].sort((a, bb) => (a.number||0) - (bb.number||0));
      const chHtml = sorted.map(ch => {
        const pub = ch.published;
        const score = ch.score || "—";
        const num = ch.number;
        return `<div style="display:flex;align-items:center;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--border);gap:4px">
          <div style="display:flex;align-items:center;gap:6px;flex:1;min-width:0">
            <span style="font-size:.7rem;color:var(--text-dim);flex-shrink:0;width:24px">Гл.${num}</span>
            <button onclick="bsShowChapter('${b.slug}',${num})" style="background:none;border:none;color:var(--text);font-size:.76rem;cursor:pointer;text-align:left;padding:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:110px">${ch.title||("Глава "+num)}</button>
          </div>
          <div style="display:flex;align-items:center;gap:5px;flex-shrink:0">
            <span style="font-size:.68rem;color:var(--amber)">★${score}</span>
            ${pub
              ? `<span style="font-size:.62rem;color:var(--green);background:rgba(16,185,129,.12);padding:1px 5px;border-radius:9px">✓</span>`
              : `<button onclick="bsPublish('${b.slug}',${num})" style="font-size:.62rem;color:var(--text-dim);background:var(--bg);border:1px solid var(--border);padding:1px 5px;border-radius:9px;cursor:pointer">↑ Публ</button>`
            }
          </div>
        </div>`;
      }).join("");

      document.getElementById("bs-chapters").innerHTML = `
        <div style="font-size:.65rem;color:var(--text-dim);letter-spacing:.1em;margin-bottom:6px">📋 ГЛАВЫ</div>
        ${chHtml || '<div style="color:var(--text-dim)">Нет глав</div>'}`;

      // Разведка рынка
      const sc = stats.scout || {};
      if (sc.trending_genres) {
        document.getElementById("bs-scout").innerHTML = `
          <div style="font-size:.65rem;color:var(--text-dim);letter-spacing:.1em;margin-bottom:8px">🔭 РАЗВЕДКА РЫНКА</div>
          <div style="font-size:.78rem;color:var(--text);line-height:1.8">
            ${sc.trending_genres ? `<b>Тренды:</b> ${sc.trending_genres.join(", ")}<br>` : ""}
            ${sc.top_mechanics ? `<b>Механики:</b> ${sc.top_mechanics.join(", ")}<br>` : ""}
            ${sc.competitor_weaknesses ? `<b>Слабости:</b> ${sc.competitor_weaknesses.join(", ")}<br>` : ""}
            ${sc.recommended_hooks ? `<b>Хуки:</b> ${sc.recommended_hooks.join(", ")}<br>` : ""}
            ${sc.avoid ? `<b>Избегать:</b> ${sc.avoid.join(", ")}` : ""}
          </div>`;
      }
    } catch(e) {
      document.getElementById("bs-stats").innerHTML = `<div style="color:var(--red)">Ошибка: ${e.message}</div>`;
    }
  }

  async function bsShowChapter(slug, num) {
    const box = document.getElementById("bs-chapter-text");
    if (_bsChapterOpen === num) { box.style.display="none"; _bsChapterOpen=null; return; }
    box.style.display = "block";
    box.innerHTML = "Загрузка...";
    _bsChapterOpen = num;
    try {
      const r = await fetch("/bs/books/" + slug + "/chapters/" + num);
      const d = await r.json();
      const text = (d.content || d.text || "нет текста").replace(/</g,"&lt;").replace(/>/g,"&gt;");
      box.innerHTML = `<div style="display:flex;justify-content:space-between;margin-bottom:10px;font-size:.7rem;color:var(--text-dim)">
        <span>Глава ${num} · ★${d.score||"—"} · ${d.word_count||"?"} слов</span>
        <button onclick="document.getElementById('bs-chapter-text').style.display='none';_bsChapterOpen=null" style="background:none;border:none;color:var(--text-dim);cursor:pointer;font-size:1rem;padding:0">✕</button>
      </div>${text}`;
    } catch(e) { box.innerHTML = "Ошибка: " + e.message; }
  }

  async function bsGenerate(slug) {
    const r = await fetch("/bs/books/"+slug+"/generate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({book_slug:slug,target_words:2000})});
    const d = await r.json();
    showToast(d.ok ? "✅ Глава "+d.queued_chapter+" в очереди" : "❌ "+(d.detail||"Ошибка"));
    setTimeout(loadBookStudio, 3000);
  }

  async function bsPublish(slug, num) {
    const r = await fetch("/bs/books/"+slug+"/publish/"+num,{method:"POST"});
    const d = await r.json();
    showToast((d.ok||d.published) ? "✅ Опубликовано" : "❌ "+(d.detail||"Ошибка"));
    setTimeout(loadBookStudio, 2000);
  }"""

with open("/app/app/static/hq.html", "r", encoding="utf-8") as f:
    html = f.read()

# Заменяем вкладку
OLD_TAB_START = "      <!-- TAB: BOOKSTUDIO -->"
OLD_TAB_END = "      </div>\n\n      <!-- TAB: AUDIT -->"
idx_ts = html.find(OLD_TAB_START)
idx_te = html.find(OLD_TAB_END)
if idx_ts < 0 or idx_te < 0:
    print(f"TAB not found: start={idx_ts}, end={idx_te}")
else:
    html = html[:idx_ts] + NEW_TAB + "\n\n      <!-- TAB: AUDIT -->" + html[idx_te + len(OLD_TAB_END):]
    print("TAB OK")

# Заменяем JS
OLD_JS_START = "  // Book Studio — загрузка данных через /stats"
OLD_JS_END = "    setTimeout(loadBookStudio, 3000);\n  }"
idx_js_s = html.find(OLD_JS_START)
idx_js_e = html.find(OLD_JS_END)
if idx_js_s < 0 or idx_js_e < 0:
    print(f"JS not found: start={idx_js_s}, end={idx_js_e}")
else:
    idx_js_e += len(OLD_JS_END)
    html = html[:idx_js_s] + NEW_JS + html[idx_js_e:]
    print("JS OK")

with open("/app/app/static/hq.html", "w", encoding="utf-8") as f:
    f.write(html)
print(f"Written {len(html)} chars")
