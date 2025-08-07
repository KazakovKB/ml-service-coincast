import asyncio, json, os
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from client import ApiClient, ApiError

TOKEN = os.getenv("TG_BOT_TOKEN")

bot = Bot(token=TOKEN,
          default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2))
dp  = Dispatcher()

_clients: dict[int, ApiClient] = {}
def api_for(tgid: int) -> ApiClient:
    return _clients.setdefault(tgid, ApiClient())


# helper
async def safe_call(msg: types.Message, coro):
    """
    Выполняет REST-запрос, выводит понятную ошибку.
    Возвращает результат или None.
    """
    try:
        return await coro
    except ApiError as err:
        if err.status == 401:
            await msg.answer("🚫 Сначала авторизуйтесь:\n`/login email pass`")
        elif err.status == 402:
            await msg.answer("💸 Недостаточно кредитов")
        elif err.status == 500:
            await msg.answer(f"⚠️ Ошибка модели:\n```{err.detail}```")
        else:
            await msg.answer(f"❌ `{err.detail or err.status}`")
        return None


@dp.message(F.text == "/start")
async def start(msg: types.Message):
    await msg.answer(
        "👋 *Coincast Bot*\n\n"
        "`/register email pass` – регистрация\n"
        "`/login email pass` – войти\n"
        "`/balance` – баланс\n"
        "`/topup 100` – пополнить\n"
        "`/tx` – история транзакций\n"
        "`/predict Model JSON` – предсказать\n"
        "`/ph` – история предсказаний"
    )


@dp.message(F.text.startswith("/register"))
async def register(msg: types.Message):
    try:
        _, email, pwd = msg.text.split(maxsplit=2)
    except ValueError:
        await msg.answer("Формат: `/register email pass`")
        return

    if await safe_call(msg, api_for(msg.from_user.id).register(email, pwd)):
        await msg.answer("✅ Зарегистрирован и залогинен")

@dp.message(F.text.startswith("/login"))
async def login(msg: types.Message):
    try:
        _, email, pwd = msg.text.split(maxsplit=2)
    except ValueError:
        await msg.answer("Формат: `/login email pass`")
        return

    if await safe_call(msg, api_for(msg.from_user.id).login(email, pwd)):
        await msg.answer("✅ Логин успешен")


@dp.message(F.text == "/balance")
async def balance(msg: types.Message):
    bal = await safe_call(msg, api_for(msg.from_user.id).balance())
    if bal is not None:
        await msg.answer(f"💰 Баланс: *{bal}*")

@dp.message(F.text.startswith("/topup"))
async def topup(msg: types.Message):
    parts = msg.text.split(maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        await msg.answer("Формат: `/topup 100`")
        return

    bal = await safe_call(msg,
                          api_for(msg.from_user.id).topup(int(parts[1]), "telegram"))
    if bal is not None:
        await msg.answer(f"✅ Новый баланс: *{bal}*")

@dp.message(F.text == "/tx")
async def tx(msg: types.Message):
    txs = await safe_call(msg, api_for(msg.from_user.id).transactions())
    if not txs:
        return

    lines = [
        f"{t['created_at'][:16]} • {t['tx_type']} • {t['amount']} → {t['balance_after']}"
        for t in txs
    ]
    await msg.answer("```\n" + "\n".join(lines) + "\n```")


@dp.message(F.text.startswith("/predict"))
async def predict(msg: types.Message):
    try:
        _, model, raw = msg.text.split(maxsplit=2)
        rows = json.loads(raw.strip("` "))
        if isinstance(rows, dict):
            rows = [rows]
    except Exception:
        await msg.answer("Пример:\n```/predict Demo [{\"f1\":1}]```")
        return

    job = await safe_call(msg, api_for(msg.from_user.id).predict(model, rows))
    if not job:
        return

    await msg.answer(
        f"📈 Прогноз:\n```{job['predictions']}```\n"
        f"🧠 Строк: *{len(job['predictions'])}*\n"
        f"💸 Списано: *{job['cost']}*"
    )


@dp.message(F.text == "/ph")
async def pred_history(msg: types.Message):
    jobs = await safe_call(msg, api_for(msg.from_user.id).pred_history())
    if not jobs:
        return

    lines = [
        f"{j['created_at'][:16]} • {j['model_name']} • {j['cost']}"
        for j in jobs
    ]
    await msg.answer("```\n" + "\n".join(lines) + "\n```")


async def main():
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
    )

if __name__ == "__main__":
    asyncio.run(main())