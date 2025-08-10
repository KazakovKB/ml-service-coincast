import asyncio, json, os, html
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from client import ApiClient, ApiError

TOKEN = os.getenv("TG_BOT_TOKEN")

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp  = Dispatcher()

_clients: dict[int, ApiClient] = {}
def api_for(tgid: int) -> ApiClient:
    return _clients.setdefault(tgid, ApiClient())


# helper
async def safe_call(msg: types.Message, coro):
    """
    Выполняет REST-запрос
    Возвращает результат или None.
    """
    try:
        return await coro
    except ApiError as err:
        detail = html.escape(err.detail or str(err.status))
        if err.status == 401:
            await msg.answer("🚫 Сначала авторизуйтесь:\n<code>/login email pass</code>")
        elif err.status == 402:
            await msg.answer("💸 Недостаточно кредитов")
        elif err.status == 500:
            await msg.answer(f"⚠️ Ошибка модели:\n<pre><code>{detail}</code></pre>")
        else:
            await msg.answer(f"❌ <code>{detail}</code>")
        return None


@dp.message(F.text == "/start")
async def start(msg: types.Message):
    await msg.answer(
        "👋 <b>Coincast Bot</b>\n\n"
        "<code>/register email pass</code> – регистрация\n"
        "<code>/login email pass</code> – войти\n"
        "<code>/balance</code> – баланс\n"
        "<code>/topup 100</code> – пополнить\n"
        "<code>/tx</code> – история транзакций\n"
        "<code>/predict Model JSON</code> – предсказать\n"
        "<code>/ph</code> – история предсказаний\n"
        "<code>/job id</code> – статус задачи"
    )


@dp.message(F.text.startswith("/register"))
async def register(msg: types.Message):
    try:
        _, email, pwd = msg.text.split(maxsplit=2)
    except ValueError:
        await msg.answer("Формат: <code>/register email pass</code>")
        return

    if await safe_call(msg, api_for(msg.from_user.id).register(email, pwd)):
        await msg.answer("✅ Зарегистрирован и залогинен")


@dp.message(F.text.startswith("/login"))
async def login(msg: types.Message):
    try:
        _, email, pwd = msg.text.split(maxsplit=2)
    except ValueError:
        await msg.answer("Формат: <code>/login email pass</code>")
        return

    if await safe_call(msg, api_for(msg.from_user.id).login(email, pwd)):
        await msg.answer("✅ Логин успешен")


@dp.message(F.text == "/balance")
async def balance(msg: types.Message):
    bal = await safe_call(msg, api_for(msg.from_user.id).balance())
    if bal is not None:
        await msg.answer(f"💰 Баланс: <b>{bal}</b>")


@dp.message(F.text.startswith("/topup"))
async def topup(msg: types.Message):
    parts = msg.text.split(maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        await msg.answer("Формат: <code>/topup 100</code>")
        return

    bal = await safe_call(msg, api_for(msg.from_user.id).topup(int(parts[1]), "telegram"))
    if bal is not None:
        await msg.answer(f"✅ Новый баланс: <b>{bal}</b>")


@dp.message(F.text == "/tx")
async def tx(msg: types.Message):
    txs = await safe_call(msg, api_for(msg.from_user.id).transactions())
    if not txs:
        return

    lines = [
        f"{html.escape(t['created_at'][:16])} • {html.escape(str(t['tx_type']))} • "
        f"{html.escape(str(t['amount']))} → {html.escape(str(t['balance_after']))}"
        for t in txs
    ]
    body = "\n".join(lines)
    await msg.answer(f"<pre><code>{body}</code></pre>")


@dp.message(F.text.startswith("/predict"))
async def predict(msg: types.Message):
    try:
        _, model, raw = msg.text.split(maxsplit=2)
        rows = json.loads(raw.strip("` "))
        if isinstance(rows, dict):
            rows = [rows]
    except Exception:
        await msg.answer("Пример:\n<pre><code>/predict Demo [{\"f1\":1}]</code></pre>")
        return

    job = await safe_call(msg, api_for(msg.from_user.id).predict(model, rows))
    if not job:
        return

    jid = html.escape(str(job.get("id")))
    status = html.escape(str(job.get("status", "PENDING")))
    await msg.answer(
        "🧾 Задача отправлена в очередь\n"
        f"🆔 ID: <b>{jid}</b> • Статус: <b>{status}</b>\n"
        f"Проверить: <code>/job {jid}</code>"
    )


@dp.message(F.text == "/ph")
async def pred_history(msg: types.Message):
    jobs = await safe_call(msg, api_for(msg.from_user.id).pred_history())
    if not jobs:
        return

    lines = [
        f"{html.escape(j.get('created_at','')[:16])} • "
        f"{html.escape(j.get('model_name',''))} • "
        f"{html.escape(str(j.get('cost', 0)))}"
        for j in jobs
    ]
    body = "\n".join(lines)
    await msg.answer(f"<pre><code>{body}</code></pre>")


@dp.message(F.text.startswith("/job"))
async def job_view(msg: types.Message):
    parts = msg.text.split(maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        await msg.answer("Формат: <code>/job 123</code>")
        return

    job = await safe_call(msg, api_for(msg.from_user.id).pred_job(int(parts[1])))
    if not job:
        return

    status = html.escape(job.get("status", "UNKNOWN"))
    jid    = html.escape(str(job.get("id")))
    model  = html.escape(job.get("model_name", ""))
    ts     = html.escape(job.get("created_at", "")[:16])

    lines = [
        f"🆔 <b>{jid}</b> • <b>{status}</b>",
        f"🧠 Модель: <b>{model}</b>",
    ]
    if ts:
        lines.append(f"🕒 {ts}")

    if status == "OK":
        preds = job.get("predictions", []) or []
        cost  = job.get("cost", 0)
        lines.append(f"💸 Стоимость: <b>{html.escape(str(cost))}</b>")
        lines.append(f"✅ Строк: <b>{len(preds)}</b>")
        if preds:
            preview = preds[:10]
            preview_json = html.escape(json.dumps(preview, ensure_ascii=False, indent=2))
            more = " …" if len(preds) > 10 else ""
            lines.append(f"<pre><code>{preview_json}{more}</code></pre>")

    elif status == "ERROR":
        err = html.escape(job.get("error", "unknown"))
        lines.append(f"⚠️ Ошибка:\n<pre><code>{err}</code></pre>")

    else:
        lines.append(f"⌛ Задача ещё выполняется. Повторите <code>/job {jid}</code> позже.")

    await msg.answer("\n".join(lines))


async def main():
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
    )

if __name__ == "__main__":
    asyncio.run(main())