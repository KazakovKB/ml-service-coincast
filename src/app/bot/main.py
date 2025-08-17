import asyncio, json, os, html
from typing import Optional

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ContentType
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from client import ApiClient, ApiError
from keyboards import main_menu, models_kb, pred_source_kb, job_actions_kb
from parsers import parse_document

TOKEN = os.getenv("TG_BOT_TOKEN")
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()

_clients: dict[int, ApiClient] = {}
def api_for(tgid: int) -> ApiClient:
    return _clients.setdefault(tgid, ApiClient())

class PredictFSM(StatesGroup):
    choosing_model = State()
    waiting_json   = State()
    waiting_file   = State()

async def safe_call(msg: types.Message | types.CallbackQuery, coro):
    try:
        return await coro
    except ApiError as err:
        detail = html.escape(err.detail or str(err.status))
        chat = msg.message if isinstance(msg, types.CallbackQuery) else msg
        if err.status == 401:
            await chat.answer("🚫 Please sign in first:\n<code>/login email pass</code>")
        elif err.status == 402:
            await chat.answer("💸 Not enough credits. Top up with: <code>/topup 100</code>")
        elif err.status == 500:
            await chat.answer(f"⚠️ Model error:\n<pre><code>{detail}</code></pre>")
        else:
            await chat.answer(f"❌ <code>{detail}</code>")
        return None

def _is_authed(user_id: int) -> bool:
    return api_for(user_id)._token is not None


@dp.message(F.text == "/start")
async def start(msg: types.Message):
    await msg.answer(
        "👋 <b>Coincast Bot</b>\n"
        "A simple interface for predictions and balance management.",
        reply_markup=main_menu(_is_authed(msg.from_user.id))
    )

@dp.callback_query(F.data == "menu:home")
async def menu_home(cb: types.CallbackQuery):
    await cb.message.edit_text(
        "🏠 Main menu",
        reply_markup=main_menu(_is_authed(cb.from_user.id))
    )
    await cb.answer()

@dp.callback_query(F.data == "menu:help")
async def menu_help(cb: types.CallbackQuery):
    await cb.message.edit_text(
        "Commands:\n"
        "<code>/register email pass</code>\n"
        "<code>/login email pass</code>\n"
        "<code>/balance</code>, <code>/topup 100</code>\n"
        "<code>/tx</code> — transactions\n"
        "<code>/ph</code> — prediction history\n"
        "<code>/predict Model JSON</code>\n"
        "<code>/job id</code> — job status\n"
        "Or just use the buttons below.",
        reply_markup=main_menu(_is_authed(cb.from_user.id))
    )
    await cb.answer()


@dp.callback_query(F.data == "menu:login")
async def cb_login(cb: types.CallbackQuery):
    await cb.message.answer("Format: <code>/login email pass</code>")
    await cb.answer()

@dp.callback_query(F.data == "menu:register")
async def cb_register(cb: types.CallbackQuery):
    await cb.message.answer("Format: <code>/register email pass</code>")
    await cb.answer()

@dp.message(F.text.startswith("/register"))
async def register(msg: types.Message):
    try:
        _, email, pwd = msg.text.split(maxsplit=2)
    except ValueError:
        await msg.answer("Format: <code>/register email pass</code>")
        return
    if await safe_call(msg, api_for(msg.from_user.id).register(email, pwd)):
        await msg.answer("✅ Registered and signed in", reply_markup=main_menu(True))

@dp.message(F.text.startswith("/login"))
async def login(msg: types.Message):
    try:
        _, email, pwd = msg.text.split(maxsplit=2)
    except ValueError:
        await msg.answer("Format: <code>/login email pass</code>")
        return
    if await safe_call(msg, api_for(msg.from_user.id).login(email, pwd)):
        await msg.answer("✅ Sign-in successful", reply_markup=main_menu(True))


@dp.callback_query(F.data == "menu:balance")
async def cb_balance(cb: types.CallbackQuery):
    bal = await safe_call(cb, api_for(cb.from_user.id).balance())
    if bal is not None:
        await cb.message.edit_text(f"💰 Balance: <b>{bal}</b>", reply_markup=main_menu(True))
    await cb.answer()

@dp.message(F.text == "/balance")
async def balance(msg: types.Message):
    bal = await safe_call(msg, api_for(msg.from_user.id).balance())
    if bal is not None:
        await msg.answer(f"💰 Balance: <b>{bal}</b>")

@dp.message(F.text.startswith("/topup"))
async def topup(msg: types.Message):
    parts = msg.text.split(maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        await msg.answer("Format: <code>/topup 100</code>")
        return
    bal = await safe_call(msg, api_for(msg.from_user.id).topup(int(parts[1]), "telegram"))
    if bal is not None:
        await msg.answer(f"✅ New balance: <b>{bal}</b>")

@dp.callback_query(F.data == "menu:tx")
async def cb_tx(cb: types.CallbackQuery):
    txs = await safe_call(cb, api_for(cb.from_user.id).transactions())
    if not txs:
        return
    lines = [
        f"{html.escape(t['created_at'][:16])} • {html.escape(str(t['tx_type']))} • "
        f"{html.escape(str(t['amount']))} → {html.escape(str(t['balance_after']))}"
        for t in txs
    ]
    await cb.message.edit_text(f"<pre><code>{'\n'.join(lines)}</code></pre>", reply_markup=main_menu(True))
    await cb.answer()


@dp.callback_query(F.data == "menu:predict")
async def cb_predict(cb: types.CallbackQuery, state: FSMContext):
    models = await safe_call(cb, api_for(cb.from_user.id).models())
    if not models:
        return
    await state.clear()
    await cb.message.edit_text("Choose a model:", reply_markup=models_kb(models))
    await cb.answer()

@dp.callback_query(F.data.startswith("model:"))
async def choose_model(cb: types.CallbackQuery, state: FSMContext):
    model = cb.data.split(":", 1)[1]
    await state.update_data(model=model)
    await state.set_state(PredictFSM.choosing_model)
    await cb.message.edit_text(
        f"Model: <b>{html.escape(model)}</b>\nChoose data source:",
        reply_markup=pred_source_kb()
    )
    await cb.answer()

@dp.callback_query(F.data == "pred:json")
async def want_json(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(PredictFSM.waiting_json)
    await cb.message.edit_text(
        "Send a JSON array (or a single object):\n"
        "<pre><code>[{\"timestamp\":\"2024-01-01\",\"price\":10.5,\"f1\":1}]</code></pre>"
    )
    await cb.answer()

@dp.message(PredictFSM.waiting_json, F.content_type == ContentType.TEXT)
async def handle_json(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    model: Optional[str] = data.get("model")
    if not model:
        await msg.answer("Pick a model first: /start → Predict")
        await state.clear()
        return

    try:
        rows = json.loads(msg.text.strip("` "))
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            raise ValueError("JSON must be a list or an object")
    except Exception as e:
        await msg.answer(f"❌ Invalid JSON: <code>{html.escape(str(e))}</code>")
        return

    job = await safe_call(msg, api_for(msg.from_user.id).predict(model, rows))
    if not job:
        return
    jid = int(job["id"])
    await msg.answer(
        f"🧾 Job created\n🆔 <b>{jid}</b> • <b>{html.escape(job.get('status','PENDING'))}</b>",
        reply_markup=job_actions_kb(jid)
    )
    await state.clear()

@dp.callback_query(F.data == "pred:file")
async def want_file(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(PredictFSM.waiting_file)
    await cb.message.edit_text(
        "Send a CSV/JSON file (XLSX/Parquet are supported if dependencies are installed)."
    )
    await cb.answer()

@dp.message(PredictFSM.waiting_file, F.document)
async def handle_file(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    model: Optional[str] = data.get("model")
    if not model:
        await msg.answer("Pick a model first: /start → Predict")
        await state.clear()
        return

    try:
        rows, summary = await parse_document(bot, msg.document)
    except Exception as e:
        await msg.answer(f"❌ Could not parse the file: <code>{html.escape(str(e))}</code>")
        return

    job = await safe_call(msg, api_for(msg.from_user.id).predict(model, rows))
    if not job:
        return
    jid = int(job["id"])
    await msg.answer(
        f"📎 {html.escape(summary)}\n"
        f"🧾 Job created\n🆔 <b>{jid}</b> • <b>{html.escape(job.get('status','PENDING'))}</b>",
        reply_markup=job_actions_kb(jid)
    )
    await state.clear()


@dp.callback_query(F.data == "menu:ph")
async def cb_history(cb: types.CallbackQuery):
    jobs = await safe_call(cb, api_for(cb.from_user.id).pred_history())
    if not jobs:
        return
    lines = [
        f"{html.escape(j.get('created_at','')[:16])} • "
        f"{html.escape(j.get('model_name',''))} • "
        f"{html.escape(str(j.get('cost', 0)))}"
        for j in jobs
    ]
    await cb.message.edit_text(f"<pre><code>{'\n'.join(lines) or '—'}</code></pre>",
                               reply_markup=main_menu(True))
    await cb.answer()

@dp.message(F.text.startswith("/job"))
async def job_cmd(msg: types.Message):
    parts = msg.text.split(maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        await msg.answer("Usage: <code>/job 123</code>")
        return
    await _send_job_view(msg, int(parts[1]))

@dp.callback_query(F.data.startswith("job:"))
async def job_cb(cb: types.CallbackQuery):
    job_id = int(cb.data.split(":", 1)[1])
    await _send_job_view(cb.message, job_id)
    await cb.answer()

async def _send_job_view(target: types.Message, job_id: int):
    job = await safe_call(target, api_for(target.chat.id).pred_job(job_id))
    if not job:
        return
    status = html.escape(job.get("status", "UNKNOWN"))
    jid    = html.escape(str(job.get("id")))
    model  = html.escape(job.get("model_name", ""))
    ts     = html.escape((job.get("created_at") or "")[:16])

    lines = [f"🆔 <b>{jid}</b> • <b>{status}</b>", f"🧠 Model: <b>{model}</b>"]
    if ts: lines.append(f"🕒 {ts}")

    if status == "OK":
        preds = job.get("predictions", []) or []
        cost  = job.get("cost", 0)
        lines.append(f"💸 Cost: <b>{html.escape(str(cost))}</b>")
        lines.append(f"✅ Rows: <b>{len(preds)}</b>")
        if preds:
            preview_json = html.escape(json.dumps(preds[:20], ensure_ascii=False, indent=2))
            more = " …" if len(preds) > 20 else ""
            lines.append(f"<pre><code>{preview_json}{more}</code></pre>")
    elif status == "ERROR":
        err = html.escape(job.get("error", "unknown"))
        lines.append(f"⚠️ Error:\n<pre><code>{err}</code></pre>")
    else:
        lines.append(f"⌛ Processing…")

    await target.answer("\n".join(lines), reply_markup=job_actions_kb(int(jid)))


@dp.message(F.text == "/tx")
async def tx(msg: types.Message):
    txs = await safe_call(msg, api_for(msg.from_user.id).transactions())
    if not txs: return
    lines = [
        f"{html.escape(t['created_at'][:16])} • {html.escape(str(t['tx_type']))} • "
        f"{html.escape(str(t['amount']))} → {html.escape(str(t['balance_after']))}"
        for t in txs
    ]
    await msg.answer(f"<pre><code>{'\n'.join(lines)}</code></pre>")

@dp.message(F.text == "/ph")
async def pred_history(msg: types.Message):
    jobs = await safe_call(msg, api_for(msg.from_user.id).pred_history())
    if not jobs: return
    lines = [
        f"{html.escape(j.get('created_at','')[:16])} • "
        f"{html.escape(j.get('model_name',''))} • "
        f"{html.escape(str(j.get('cost', 0)))}"
        for j in jobs
    ]
    await msg.answer(f"<pre><code>{'\n'.join(lines)}</code></pre>")

async def main():
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
    )

if __name__ == "__main__":
    asyncio.run(main())