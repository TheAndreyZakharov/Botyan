import json
import os
import random
import asyncio
import datetime

DATA_FILE = "data/economy_data.json"
START_BALANCE = 100_000
DAILY_BONUS = 1000

SLOTS = [
    ("🍒", 2),
    ("🍋", 3),
    ("🍇", 4),
    ("🍀", 5),
    ("💎", 10)
]

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def ensure_user_exists(user_id: int):
    data = load_data()
    str_id = str(user_id)
    today = datetime.date.today().isoformat()
    if str_id not in data:
        data[str_id] = {"balance": START_BALANCE, "last_daily": today}
        save_data(data)
    elif "last_daily" not in data[str_id]:
        data[str_id]["last_daily"] = today
        save_data(data)

def add_daily_bonus_if_needed(user_id: int):
    data = load_data()
    str_id = str(user_id)
    today = datetime.date.today().isoformat()
    ensure_user_exists(user_id)
    user = data[str_id]
    last_daily = user.get("last_daily")
    if last_daily != today:
        user["balance"] += DAILY_BONUS
        user["last_daily"] = today
        save_data(data)

def get_balance(user_id: int) -> int:
    ensure_user_exists(user_id)
    add_daily_bonus_if_needed(user_id)
    data = load_data()
    return data[str(user_id)]["balance"]

def update_balance(user_id: int, amount: int):
    ensure_user_exists(user_id)
    add_daily_bonus_if_needed(user_id)
    data = load_data()
    data[str(user_id)]["balance"] += amount
    save_data(data)

async def slots_spin(message, bet: int):
    user_id = message.from_user.id
    ensure_user_exists(user_id)
    add_daily_bonus_if_needed(user_id)
    balance = get_balance(user_id)
    if bet > balance:
        return "❌ У тебя недостаточно монет."
    if bet <= 0:
        return "❗ Ставка должна быть положительной."

    sent_msg = await message.reply("🎰 Вращаем барабаны...")

    for _ in range(4):
        rnd = [random.choice(SLOTS)[0] for _ in range(3)]
        await sent_msg.edit_text(" ".join(rnd))
        await asyncio.sleep(0.2)

    final = [random.choice(SLOTS) for _ in range(3)]
    symbols = [item[0] for item in final]
    await sent_msg.edit_text(" ".join(symbols))

    if symbols[0] == symbols[1] == symbols[2]:
        coef = final[0][1]
        win = bet * coef
        update_balance(user_id, win)
        text = f"🎉 {message.from_user.mention_html()}, ты выиграл <b>{win}</b> монет! (x{coef})"
    else:
        update_balance(user_id, -bet)
        text = f"😢 {message.from_user.mention_html()}, не повезло. Потеряно <b>{bet}</b> монет."

    await asyncio.sleep(0.4)
    await sent_msg.edit_text(f"{' '.join(symbols)}\n\n{text}", parse_mode="HTML")
    return None

async def daily_bonus_handler(message):
    user_id = message.from_user.id
    data = load_data()
    str_id = str(user_id)
    today = datetime.date.today().isoformat()
    ensure_user_exists(user_id)
    user = data[str_id]
    last_daily = user.get("last_daily")
    if last_daily == today:
        await message.reply("Сегодня ты уже получал ежедневный бонус!")
    else:
        add_daily_bonus_if_needed(user_id)
        await message.reply(f"Тебе начислено {DAILY_BONUS} монет!")

