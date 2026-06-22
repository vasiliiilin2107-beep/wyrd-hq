"""
Авито OAuth callback — авторизация WYRD аккаунта.
После получения токена сохраняет в диспетчер (клиент neiroceh).
"""
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

CLIENT_ID     = "idAgm2f7oBeBgbB4ID0B"
CLIENT_SECRET = "VGLI7cjiykhXfqdYEboFPkwKw0UJrDKDTROHhTQV"
REDIRECT_URI  = "https://wyrd.su/avito/callback"

DISPATCHER_URL    = "http://147.45.212.155:8100"
DISPATCHER_SECRET = "4fb8c604cf845665a887e7da8029dd9c6bca23169848bafe"


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

    if "access_token" not in data:
        return HTMLResponse(f"<h2>Ошибка токена</h2><pre>{data}</pre>", status_code=400)

    token = data["access_token"]
    credential = f"{CLIENT_ID}:{CLIENT_SECRET}"

    # Сохраняем токен в диспетчер
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{DISPATCHER_URL}/internal/set-avito-token",
                json={"client_id": "neiroceh", "avito_token": credential, "access_token": token},
                headers={"X-Secret": DISPATCHER_SECRET},
                timeout=5,
            )
        dispatcher_ok = True
    except Exception:
        dispatcher_ok = False

    return HTMLResponse(f"""
    <h2>✅ Авито WYRD подключён!</h2>
    <p>Диспетчер {'обновлён ✅' if dispatcher_ok else '⚠️ не обновлён (сохрани токен вручную)'}</p>
    <pre style='background:#f0f0f0;padding:10px;word-break:break-all'>{token[:40]}…</pre>
    """)


@router.get("/avito/auth", response_class=HTMLResponse)
async def avito_auth_start():
    from urllib.parse import urlencode
    params = urlencode({
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "messenger:read messenger:write items:info autoload:reports",
        "state": "wyrd-main",
    })
    url = f"https://avito.ru/oauth?{params}"
    return HTMLResponse(f'<a href="{url}">Авторизовать WYRD в Авито</a>')
