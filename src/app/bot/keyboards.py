from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu(is_authed: bool) -> InlineKeyboardMarkup:
    if not is_authed:
        kb = [
            [InlineKeyboardButton(text="🔑 Login", callback_data="menu:login"),
             InlineKeyboardButton(text="🆕 Register", callback_data="menu:register")],
            [InlineKeyboardButton(text="ℹ️ Help", callback_data="menu:help")],
        ]
    else:
        kb = [
            [InlineKeyboardButton(text="💰 Balance", callback_data="menu:balance"),
             InlineKeyboardButton(text="📈 Predict", callback_data="menu:predict")],
            [InlineKeyboardButton(text="📜 Transactions", callback_data="menu:tx"),
             InlineKeyboardButton(text="🧠 History", callback_data="menu:ph")],
        ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def models_kb(models: list[str]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=m, callback_data=f"model:{m}")] for m in models]
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def pred_source_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧾 Send JSON", callback_data="pred:json")],
        [InlineKeyboardButton(text="📎 Upload file", callback_data="pred:file")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="menu:predict")],
    ])

def job_actions_kb(job_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh status", callback_data=f"job:{job_id}")],
        [InlineKeyboardButton(text="🧠 History", callback_data="menu:ph")],
    ])