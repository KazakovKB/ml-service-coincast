import os, json, io
from typing import Optional, Any, List, Dict
from urllib.parse import urlencode, quote

import httpx
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, status, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, UTC

API_BASE = os.getenv("API_BASE")
templates = Jinja2Templates(directory="src/app/web/templates")
templates.env.globals["now"] = lambda: datetime.now(UTC)
router = APIRouter(tags=["Web UI"])



def _is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request", "").lower() == "true"

def _token(request: Request) -> Optional[str]:
    return request.cookies.get("access_token")

async def _guard(request: Request) -> str:
    token = _token(request)
    if not token:
        nxt = quote(request.url.path)
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": f"/login?reason=required&next={nxt}"}
        )
    return token

async def _api(method: str, path: str, token: Optional[str] = None, **kwargs) -> httpx.Response:
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(base_url=API_BASE) as cli:
        return await cli.request(method, path, headers=headers, **kwargs)

def _alert_partial(request: Request, message: str, tone: str = "error", status_code: int = 400) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/_alert.html",
        {"request": request, "message": message, "tone": tone},
        status_code=status_code,
    )

def _redirect_to_login(request: Request, reason: str = "auth_required", next_path: str | None = None):
    next_url = next_path or request.url.path
    qs = urlencode({"reason": reason, "next": next_url})

    if _is_htmx(request):
        resp = HTMLResponse("", status_code=401)
        resp.headers["HX-Redirect"] = f"/login?{qs}"
        resp.delete_cookie("access_token")
        return resp

    resp = RedirectResponse(f"/login?{qs}", status_code=302)
    resp.delete_cookie("access_token")
    return resp

def _redirect(request: Request, url: str):
    if _is_htmx(request):
        resp = HTMLResponse(status_code=204)
        resp.headers["HX-Redirect"] = url
        return resp
    return RedirectResponse(url, status_code=302)

def _ext(name: str) -> str:
    return (name or "").lower().rsplit(".", 1)[-1] if "." in (name or "") else ""

def _parse_json_bytes(b: bytes) -> List[Dict[str, Any]]:
    text = b.decode("utf-8").strip()
    data: Any = None

    try:
        data = json.loads(text)
    except json.JSONDecodeError as je:
        raise HTTPException(
            400,
            f"Invalid file: not a valid JSON. Fix quotes/format"
        ) from je

    if isinstance(data, dict):
        if data and all(isinstance(v, list) for v in data.values()):
            keys = list(data.keys())
            length = max(len(v) for v in data.values()) if data else 0
            rows: List[Dict[str, Any]] = []
            for i in range(length):
                rows.append({k: (data[k][i] if i < len(data[k]) else None) for k in keys})
            return rows
        return [data]

    if isinstance(data, list):
        if not all(isinstance(x, dict) for x in data):
            raise HTTPException(400, "Invalid file: unsupported JSON structure")
        return data

    raise HTTPException(400, "Invalid file: unsupported JSON structure")


async def _parse_upload(file: UploadFile) -> List[Dict[str, Any]]:
    """
    Лёгкий парсер на стороне Web-UI.
    """
    content = await file.read()
    ext = _ext(file.filename)
    ctype = (file.content_type or "").lower()

    # CSV
    if ext == "csv" or "csv" in ctype:
        text = content.decode("utf-8", errors="replace")
        import csv
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)

    # JSON
    if ext == "json" or "json" in ctype:
        return _parse_json_bytes(content)

    # Parquet
    if ext in ("parquet", "pq") or "parquet" in ctype:
        try:
            import pandas as pd
        except Exception:
            raise HTTPException(400, "Parquet parsing requires pandas+pyarrow installed")
        df = pd.read_parquet(io.BytesIO(content))
        return df.to_dict(orient="records")

    raise HTTPException(400, f"Unsupported file type: {file.filename or ctype}")

async def _load_models(request: Request, token: str) -> List[str]:
    r = await _api("GET", "/models/", token)
    if r.status_code // 100 == 4:
        return _redirect_to_login(request)

    return r.json()



@router.get("/login", response_class=HTMLResponse)
def login_get(
    request: Request,
    reason: str | None = Query(None),
    next: str | None = Query(None),
):
    info = None
    if reason in (None, "auth_required"):
        info = "Please sign in to continue."
    elif reason in ("token_expired", "token_invalid"):
        info = "Your session has expired. Please sign in again."
    elif reason == "logged_out":
        info = "You have been signed out."

    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request, "info": info, "next": next or "/"},
    )

@router.post("/login")
async def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
):
    r = await _api("POST", "/auth/login", data={"username": email, "password": password})
    if r.status_code != 200:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Invalid credentials", "next": next},
            status_code=400,
        )
    token = r.json()["access_token"]
    resp = RedirectResponse(next or "/", status_code=302)
    resp.set_cookie("access_token", token, httponly=True, max_age=60 * 60 * 24)
    return resp

@router.get("/logout")
def logout():
    resp = RedirectResponse("/login?reason=logged_out", status_code=302)
    resp.delete_cookie("access_token")
    return resp


@router.get("/register", response_class=HTMLResponse)
def register_get(request: Request, next: str | None = Query(None)):
    return templates.TemplateResponse("auth/register.html", {"request": request, "next": next or "/"})

@router.post("/register")
async def register_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
):
    r = await _api("POST", "/auth/register", json={"email": email, "password": password})
    if r.status_code != 201:
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error": "Email already registered", "next": next},
            status_code=400,
        )
    token = r.json()["access_token"]
    resp = RedirectResponse(next or "/", status_code=302)
    resp.set_cookie("access_token", token, httponly=True, max_age=60 * 60 * 24)
    return resp


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "authed": bool(_token(request))}
    )

@router.get("/balance", response_class=HTMLResponse)
async def balance(request: Request, token: str = Depends(_guard)):
    r = await _api("GET", "/account/balance", token)
    if r.status_code // 100 == 4:
        return _redirect_to_login(request, reason="token_expired")
    r.raise_for_status()
    bal = r.json().get("balance", 0)

    notice = request.query_params.get("notice")
    message = tone = None
    if notice == "not_enough_credits":
        message = "Not enough credits to run the prediction. Please top up your balance."
        tone = "warn"

    return templates.TemplateResponse(
        "account/balance.html",
        {"request": request, "balance": bal, "message": message, "tone": tone},
    )

@router.post("/topup")
async def topup(request: Request, amount: int = Form(...), token: str = Depends(_guard)):
    if amount <= 0:
        raise HTTPException(400, "Amount must be positive")
    r = await _api("POST", "/account/top-up", token, json={"amount": amount, "reason": "web top-up"})
    if r.status_code // 100 == 4:
        return _redirect_to_login(request)
    r.raise_for_status()
    return RedirectResponse("/balance", 302)


@router.get("/tx", response_class=HTMLResponse)
async def tx_history(request: Request, token: str = Depends(_guard)):
    r = await _api("GET", "/account/transactions", token)
    if r.status_code // 100 == 4:
        return _redirect_to_login(request)
    r.raise_for_status()
    return templates.TemplateResponse("account/history.html",
                                      {"request": request, "txs": r.json()})


@router.get("/predict", response_class=HTMLResponse)
async def predict_form(request: Request, token: str = Depends(_guard)):
    models = await _load_models(request, token)
    return templates.TemplateResponse("predict/form.html", {"request": request, "models": models})

@router.post("/predict", response_class=HTMLResponse)
async def predict_submit(
    request: Request,
    model_name: str = Form(...),
    file: UploadFile = File(...),
    token: str = Depends(_guard),
):
    # парсим файл
    try:
        rows = await _parse_upload(file)
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            raise ValueError("Parsed data is not a list")
    except HTTPException as e:
        if _is_htmx(request):
            return _alert_partial(request, e.detail, tone="error", status_code=e.status_code)
        models = await _load_models(request, token)
        return templates.TemplateResponse("predict/form.html",
                                          {"request": request, "models": models, "error": e.detail},
                                          status_code=e.status_code)
    except Exception as e:
        if _is_htmx(request):
            return _alert_partial(request, f"File parse error: {e}", tone="error", status_code=400)
        models = await _load_models(request, token)
        return templates.TemplateResponse("predict/form.html",
                                          {"request": request, "models": models, "error": str(e)},
                                          status_code=400)

    # отправляем в API
    r = await _api("POST", "/predict/", token, json={"model_name": model_name, "data": rows})

    if r.status_code == 401 or r.status_code == 404:
        return _redirect_to_login(request)

    if r.status_code == status.HTTP_202_ACCEPTED:
        job = r.json()
        ctx = {"request": request, "job": job}
        if _is_htmx(request):
            return templates.TemplateResponse("predict/_job_card.html", ctx, status_code=202)
        return RedirectResponse(f"/job/{job['id']}", status_code=302)

    if r.status_code == 402:
        return _redirect(request, "/balance?notice=not_enough_credits")

    if r.status_code == 422:
        msg = "Validation error"
        if _is_htmx(request):
            return _alert_partial(request, msg, tone="error", status_code=422)
        models = await _load_models(request, token)
        return templates.TemplateResponse("predict/form.html",
                                          {"request": request, "models": models, "error": msg},
                                          status_code=422)

    # иные ошибки
    try:
        detail = r.json().get("detail", r.text)
    except Exception:
        detail = r.text
    if _is_htmx(request):
        return _alert_partial(request, detail or "Prediction failed", tone="error", status_code=r.status_code)
    models = await _load_models(request, token)
    return templates.TemplateResponse("predict/form.html",
                                      {"request": request, "models": models, "error": detail or "Prediction failed"},
                                      status_code=r.status_code)


@router.get("/job/{job_id}", response_class=HTMLResponse)
async def job_view(request: Request, job_id: int, token: str = Depends(_guard)):
    r = await _api("GET", f"/predict/{job_id}", token)
    if r.status_code // 100 == 4:
        return _redirect_to_login(request)
    if r.status_code == 404:
        if _is_htmx(request):
            return _alert_partial(request, "Job not found", tone="warn", status_code=404)
        return templates.TemplateResponse("predict/show.html",
                                          {"request": request, "job": None, "error": "Job not found"},
                                          status_code=404)
    r.raise_for_status()
    job = r.json()
    ctx = {"request": request, "job": job}
    if _is_htmx(request):
        resp = templates.TemplateResponse("predict/_job_card.html", ctx)
        resp.headers["Cache-Control"] = "no-store"
        return resp
    return templates.TemplateResponse("predict/show.html", ctx)


@router.get("/ph", response_class=HTMLResponse)
async def pred_history_page(request: Request, token: str = Depends(_guard)):
    r = await _api("GET", "/predict/history", token)
    if r.status_code // 100 == 4:
        return _redirect_to_login(request)
    r.raise_for_status()
    jobs = r.json()
    return templates.TemplateResponse("predict/history.html", {"request": request, "jobs": jobs})


@router.get("/ph/partial", response_class=HTMLResponse)
async def pred_history_partial(request: Request, token: str = Depends(_guard)):
    r = await _api("GET", "/predict/history", token)

    # истёкший/недействительный токен
    if r.status_code // 100 == 4:
        return _redirect_to_login(request, reason="expired", next_path="/ph")

    if r.status_code != 200:
        return _alert_partial(request, "Failed to load history", tone="error", status_code=r.status_code)

    jobs = r.json()
    resp = templates.TemplateResponse("predict/_job_rows.html", {"request": request, "jobs": jobs})
    resp.headers["Cache-Control"] = "no-store"
    return resp