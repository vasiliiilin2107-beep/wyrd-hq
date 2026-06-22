"""
Авито OAuth callback — одноразовая авторизация.
После получения токена сохраняет в /tmp/avito_token.txt
"""
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

CLIENT_ID     = "7ph7KC6WzP-vHfbKCc5F"
CLIENT_SECRET = "G4vvXEt6Rdu554uUuGSG0uNBfUiXQfa6KWD8ZEA_"
REDIRECT_URI  = "https://wyrd.su/avito/callback"
TOKEN_FILE    = "/tmp/avito_token.txt"


@router.get("/avito/callback", response_class=HTMLResponse)
async def avito_callback(request: Request, code: str = "", error: str = ""):
    if error:
        return HTMLResponse(f"<h2>Ошибка: {error}</h2>", status_code=400)
    if not code:
        return HTMLResponse("<h2>Нет кода авторизации</h2>", status_code=400)

    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.avito.ru/token/",
            data={
                "grant_type":    "authorization_code",
                "client_id":     CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code":          code,
                "redirect_uri":  REDIRECT_URI,
            },
        )
        data = r.json()

    if "access_token" in data:
        token = data["access_token"]
        with open(TOKEN_FILE, "w") as f:
            f.write(token)
        return HTMLResponse(f"""
        <h2>✅ Авито подключён!</h2>
        <p>Токен сохранён. Можно закрыть вкладку.</p>
        <pre style='background:#f0f0f0;padding:10px;word-break:break-all'>{token[:40]}…</pre>
        """)
    else:
        return HTMLResponse(f"<h2>Ошибка токена</h2><pre>{data}</pre>", status_code=400)


@router.get("/avito/token", response_class=HTMLResponse)
async def avito_token():
    try:
        with open(TOKEN_FILE) as f:
            token = f.read().strip()
        return HTMLResponse(f"<pre>{token}</pre>")
    except FileNotFoundError:
        return HTMLResponse("<h2>Токен не найден. Пройди авторизацию.</h2>", status_code=404)
