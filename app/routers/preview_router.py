import json, os, uuid
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

PREVIEW_DIR = Path("/opt/previews")
PREVIEW_SECRET = os.getenv("PREVIEW_SECRET", "wyrd_preview_2024")
PREVIEW_BASE_URL = os.getenv("PREVIEW_BASE_URL", "https://m29g5q65uc0vw0r5zku6pukb.147.45.212.155.sslip.io")
PREVIEW_TTL_HOURS = 72

router = APIRouter(prefix="/preview", tags=["preview"])


class CreateReq(BaseModel):
    html: str
    client_name: str = ""
    price: int = 0


@router.post("/create")
async def create_preview(req: CreateReq, x_preview_secret: str = Header(...)):
    if x_preview_secret != PREVIEW_SECRET:
        raise HTTPException(403, "Forbidden")
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex[:12]
    expires = datetime.utcnow() + timedelta(hours=PREVIEW_TTL_HOURS)
    d = PREVIEW_DIR / token
    d.mkdir()
    (d / "site.html").write_text(req.html, encoding="utf-8")
    (d / "meta.json").write_text(json.dumps({
        "client_name": req.client_name,
        "price": req.price,
        "expires": expires.isoformat(),
        "created": datetime.utcnow().isoformat(),
    }, ensure_ascii=False), encoding="utf-8")
    return {"token": token, "url": f"{PREVIEW_BASE_URL}/preview/{token}", "expires": expires.isoformat()}


@router.get("/{token}", response_class=HTMLResponse)
async def view_preview(token: str):
    if not token.isalnum() or len(token) > 32:
        raise HTTPException(400, "Invalid token")
    d = PREVIEW_DIR / token
    if not d.exists():
        raise HTTPException(404, "Превью не найдено")
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    if datetime.utcnow() > datetime.fromisoformat(meta["expires"]):
        raise HTTPException(410, "Срок превью истёк")
    html = (d / "site.html").read_text(encoding="utf-8")
    name = meta.get("client_name", "")
    overlay = f"""<style>
#_no{{position:fixed;top:0;left:0;right:0;z-index:2147483647;
  background:linear-gradient(135deg,#12082aee,#1a0f35ee);
  color:#e8c97a;font-family:-apple-system,sans-serif;font-size:14px;
  padding:10px 20px;display:flex;align-items:center;justify-content:space-between;
  border-bottom:1px solid rgba(201,168,76,.35);backdrop-filter:blur(8px);}}
#_no .logo{{font-weight:800;letter-spacing:1px;font-size:15px;}}
#_no .lbl{{font-size:12px;opacity:.7;}}
#_no .badge{{background:rgba(201,168,76,.18);border:1px solid rgba(201,168,76,.45);
  color:#e8c97a;padding:3px 12px;border-radius:20px;font-size:11px;font-weight:700;letter-spacing:1px;}}
.nw{{position:fixed;font-family:-apple-system,sans-serif;font-size:11px;
  color:rgba(201,168,76,.13);font-weight:800;letter-spacing:3px;
  pointer-events:none;z-index:2147483646;user-select:none;}}
body{{margin-top:48px!important;}}
*{{-webkit-user-drag:none!important;}}
</style>
<div id="_no">
  <span class="logo">⬡ НЕЙРОЦЕХ</span>
  <span class="lbl">{"Макет: " + name if name else "Демо-версия"}</span>
  <span class="badge">ДЕМО</span>
</div>
<div class="nw" style="bottom:24px;right:24px;transform:rotate(-30deg)">НЕЙРОЦЕХ · ДЕМО</div>
<div class="nw" style="top:72px;left:32px;transform:rotate(-30deg)">НЕЙРОЦЕХ · ДЕМО</div>
<div class="nw" style="top:72px;right:32px;transform:rotate(30deg)">НЕЙРОЦЕХ · ДЕМО</div>
<div class="nw" style="bottom:24px;left:32px;transform:rotate(30deg)">НЕЙРОЦЕХ · ДЕМО</div>
<script>
document.addEventListener('contextmenu',e=>e.preventDefault());
document.addEventListener('keydown',e=>{{
  if((e.ctrlKey||e.metaKey)&&'sua'.includes(e.key.toLowerCase()))e.preventDefault();
}});
</script>"""
    html = html.replace("</body>", overlay + "\n</body>") if "</body>" in html else html + overlay
    return HTMLResponse(content=html)
