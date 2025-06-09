import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import random
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReactionTypeEmoji
from config import (
    TELEGRAM_TOKEN, OPENROUTER_API_KEYS, OPENROUTER_MODEL,
    BOT_PERSONA, BOT_AUTO_PROMPT, BOT_INTERJECT_TEMPLATE,
    ALLOWED_TG_CHAT_IDS, ALLOWED_TG_USER_ID
)
from aiogram.filters import Command
from telegram_bot.core.message_log import save_message, get_last_messages, load_messages
from telegram_bot.core.economy import get_balance, update_balance, ensure_user_exists
from telegram_bot.core.image_gen import generate_caption_from_chat, create_demotivator
from telegram_bot.core.help import get_help_embed
from telegram_bot.core.sticker_memory import add_sticker_to_memory, get_random_sticker
from telegram_bot.core.videonote_fx import process_videonote_fx
from telegram_bot.core.send_photo import get_random_createp_image
import time
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BufferedInputFile
import re
import html
import requests 
from aiogram import Router


message_counter = 0  

AVAILABLE_REACTIONS = [
    "😂", "🤣", "😄", "😊", "❤️", "🔥", "👍", "😍", "🥳", "😎", "✨", "💯", "🤝",
    "😮", "🤔", "😐", "🙃", "🤨", "🧐", "👀", "😶", "😬", "😑", "📌", "👆",
    "👎", "😢", "😡", "💔", "🤯", "😤", "⚡", "🙄", "😠", "🖕", "💩", "❗", "❓",
    "😜", "😱", "🥲", "🤗", "😘", "🤬", "😭", "😏", "🥺", "😅", "😆", "😈", "💋",
    "🍒", "🍌", "🍓", "🥒", "🍑", "🍆"
]

def convert_markdown_to_html(md):
    text = html.escape(md)
    text = re.sub(r'\*\*([^\*]+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'(?<!\*)\*([^\*]+?)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'`([^`]+?)`', r'<code>\1</code>', text)
    text = re.sub(r'```([\s\S]+?)```', r'<pre>\1</pre>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    return text


bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
current_key_index = 0
my_username = None
PREFIX = "k"

async def get_my_username():
    global my_username
    if my_username is None:
        me = await bot.get_me()
        my_username = me.username
    return my_username

def parse_custom_command(text: str):
    if not text:
        return None
    text = text.strip()
    if not text.lower().startswith(f"{PREFIX} "):
        return None
    parts = text[len(PREFIX):].strip().split()
    if not parts:
        return None
    return parts[0].lower(), parts[1:]

def is_tg_allowed(message: Message):
    if message.chat.type == "private":
        return message.from_user.id == ALLOWED_TG_USER_ID
    else:
        return message.chat.id in ALLOWED_TG_CHAT_IDS

# Фильтр: запрещённые обращения
async def handle_not_allowed(message: Message):
    if message.chat.type == "private" and message.from_user.id != ALLOWED_TG_USER_ID:
        reply_msg = await message.reply("Я не хочу общаться лично с тобой! До свидания 👋")
        save_message(reply_msg)
        return True
    if message.chat.type != "private" and message.chat.id not in ALLOWED_TG_CHAT_IDS:
        reply_msg = await message.reply("Я не собираюсь участвовать в этом чате! До свидания 👋")
        save_message(reply_msg)
        return True
    return False

async def add_reaction(message: Message):
    try:
        emoji = random.choice(AVAILABLE_REACTIONS)
        await message.react(ReactionTypeEmoji(emoji=emoji))
    except Exception:
        pass

router = Router()


# DEMOTIVATOR
async def handle_k_demo(message: Message, file_id: str = None):
    if not is_tg_allowed(message):
        if await handle_not_allowed(message): return
        return
    if not file_id:
        if message.reply_to_message and getattr(message.reply_to_message, "photo", None):
            file_id = message.reply_to_message.photo[-1].file_id
        elif getattr(message, "photo", None):
            file_id = message.photo[-1].file_id
        else:
            messages = load_messages()
            photo_ids = [m["photo_file_id"] for m in messages if not m.get("is_bot") and m.get("photo_file_id")]
            if photo_ids:
                file_id = random.choice(photo_ids)
    if not file_id:
        reply_msg = await message.reply("❌ Не найдено ни одного фото для демотиватора (прикрепи фото, ответь на фото, или отправь в чат).")
        save_message(reply_msg)
        return
    photo = await bot.get_file(file_id)
    image_bytes = await bot.download_file(photo.file_path)
    reply_msg1 = await message.reply("Делаю...")
    save_message(reply_msg1)
    caption = await generate_caption_from_chat([])
    if not caption:
        reply_msg2 = await message.reply("❌ Не удалось сгенерировать подпись для демотиватора! Проверь API-ключи или лимиты OpenRouter.")
        save_message(reply_msg2)
        return
    img = create_demotivator(image_bytes.read(), caption)
    img.seek(0)
    photo_input = BufferedInputFile(img.read(), filename="demotivator.png")
    reply_msg3 = await message.reply_photo(photo_input)
    save_message(reply_msg3)
    await add_reaction(reply_msg3)

# Фото-сообщения с caption
@dp.message(F.photo)
async def custom_command_photo_handler(message: Message):
    if not is_tg_allowed(message):
        if await handle_not_allowed(message): return
        return
    save_message(message)
    global message_counter
    message_counter += 1
    if not message.caption:
        return
    parsed = parse_custom_command(message.caption)
    if not parsed:
        return
    cmd, args = parsed
    if cmd == "demo":
        file_id = message.photo[-1].file_id
        await handle_k_demo(message, file_id)
    if random.random() < 0.01:  # 1% шанс
        await maybe_auto_interject(message)

async def maybe_auto_interject(message: Message):
    last_msgs = get_last_messages(20)
    history_text = "\n".join(f"{author}: {content}" for author, content in last_msgs)
    from config import BOT_PERSONA, BOT_AUTO_PROMPT
    prompt = BOT_AUTO_PROMPT.format(persona=BOT_PERSONA, history=history_text)
    reply = await generate_reply(prompt)
    html_reply = convert_markdown_to_html(reply or "...")
    reply_msg = await message.answer(html_reply, parse_mode=ParseMode.HTML)
    save_message(reply_msg)

@dp.message(F.sticker)
async def sticker_save_handler(message: Message):
    add_sticker_to_memory(
        message.chat.id, 
        message.sticker.file_id, 
        set_name=getattr(message.sticker, "set_name", None)
    )

async def maybe_send_random_sticker(chat_id):
    if random.random() < 0.2:  # 20% шанс отправить стикер
        file_id = get_random_sticker(bot, chat_id)
        if file_id:
            reply_msg = await bot.send_sticker(chat_id, file_id)
            save_message(reply_msg)

# Обычные текстовые команды и обращения
@dp.message(F.text)
async def custom_command_handler(message: Message):
    if not is_tg_allowed(message):
        if await handle_not_allowed(message): return
        return
    save_message(message)
    parsed = parse_custom_command(message.text)
    bot_username = await get_my_username()
    mentioned = bot_username and f"@{bot_username.lower()}" in message.text.lower()
    replied_to_bot = (
        message.reply_to_message
        and getattr(message.reply_to_message, "from_user", None)
        and getattr(message.reply_to_message.from_user, "is_bot", False)
    )
    if mentioned or replied_to_bot:
        replied_text = message.reply_to_message.text if message.reply_to_message else ""
        prompt = message.text.strip()
        if replied_text:
            history_text = "\n".join(f"{author}: {content}" for author, content in get_last_messages(100))
            context_prompt = BOT_INTERJECT_TEMPLATE.format(
                text=replied_text,
                persona=BOT_PERSONA,
                history=history_text
            )
            context_prompt += f"\n\nПользователь спросил: {prompt}"
            reply = await generate_reply(context_prompt)
        else:
            reply = await generate_reply(prompt)
        html_reply = convert_markdown_to_html(reply or "⚠️ Пусто")
        reply_msg = await message.reply(html_reply, parse_mode=ParseMode.HTML)
        save_message(reply_msg)
        await add_reaction(reply_msg)
        return

    if not parsed:
        return

    cmd, args = parsed

    if cmd == "contrast":
        await process_videonote_fx(bot, message, effect="contrast")
        return

    if cmd == "bw":
        await process_videonote_fx(bot, message, effect="bw")
        return

    if cmd == "rus":
        await process_videonote_fx(bot, message, effect="rus")
        return

    if cmd == "pic":
        import httpx
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        try:
            img_url, caption = get_random_createp_image()

            # Попытка загрузки картинки с 3 повторами
            for attempt in range(3):
                try:
                    with httpx.Client(http2=True, verify=False, timeout=10) as client:
                        response = client.get(img_url, headers={"User-Agent": "Mozilla/5.0"})
                        img_bytes = response.content
                    break
                except Exception as e:
                    if attempt == 2:
                        raise e
                    time.sleep(1)

            photo_input = BufferedInputFile(img_bytes, filename="createp.jpg")
            reply_msg = await message.reply_photo(photo_input, caption=caption)
            save_message(reply_msg)

        except Exception as e:
            reply_msg = await message.reply(f"⚠️ Не удалось получить картинку: {e}")
            save_message(reply_msg)
        return


    if cmd == "dep":
        if not args:
            reply_msg = await message.reply("❗ Укажи сумму ставки, например <code>k dep 500</code>")
            save_message(reply_msg)
            return
        try:
            bet = int(args[0])
        except Exception:
            reply_msg = await message.reply("❗ Некорректная ставка. Введи число, например <code>k dep 100</code>")
            save_message(reply_msg)
            return

        SLOTS = [("🍒", 2), ("🍋", 3), ("🍇", 4), ("🍀", 5), ("💎", 10)]
        balance = get_balance(message.from_user.id)
        if bet > balance:
            reply_msg = await message.reply("❌ У тебя недостаточно монет.")
            save_message(reply_msg)
            return
        if bet <= 0:
            reply_msg = await message.reply("❗ Ставка должна быть положительной.")
            save_message(reply_msg)
            return

        msg = await message.reply("🎰 Вращаем барабаны...")
        save_message(msg)
        previous_text = ""
        for _ in range(4):
            rnd = [random.choice(SLOTS)[0] for _ in range(3)]
            new_text = " ".join(rnd)
            if new_text != previous_text:
                await msg.edit_text(new_text)
                previous_text = new_text
            await asyncio.sleep(0.13)

        final = [random.choice(SLOTS) for _ in range(3)]
        symbols = [item[0] for item in final]
        await msg.edit_text(" ".join(symbols))

        if symbols[0] == symbols[1] == symbols[2]:
            coef = final[0][1]
            win = bet * coef
            update_balance(message.from_user.id, win)
            text = f"🎉 {message.from_user.mention_html()}, ты выиграл <b>{win}</b> монет! (x{coef})"
        else:
            update_balance(message.from_user.id, -bet)
            text = f"😢 {message.from_user.mention_html()}, не повезло. Потеряно <b>{bet}</b> монет."
        await asyncio.sleep(0.5)
        final_msg = await msg.edit_text(f"{' '.join(symbols)}\n\n{text}")
        save_message(final_msg)
        return

    if cmd == "demo":
        await handle_k_demo(message)
        return

    if cmd == "menu":
        reply_msg = await message.answer(**get_help_embed())
        save_message(reply_msg)
        return

    if cmd == "bal":
        ensure_user_exists(message.from_user.id)
        bal = get_balance(message.from_user.id)
        reply_msg = await message.reply(f"💰 {message.from_user.mention_html()}, у тебя на счету <b>{bal}</b> монет.")
        save_message(reply_msg)
        return

    if cmd == "test":
        reply = await generate_reply("Привет! Как дела?")
        html_reply = convert_markdown_to_html(reply or "⚠️ Пусто")
        reply_msg = await message.reply(html_reply, parse_mode=ParseMode.HTML)
        save_message(reply_msg)
        await add_reaction(reply_msg)
        return

    if cmd == "limit":
        global current_key_index
        try:
            key = OPENROUTER_API_KEYS[current_key_index]
            headers = {"Authorization": f"Bearer {key}"}
            response = requests.get("https://openrouter.ai/api/v1/auth/key", headers=headers)
            if response.ok:
                data = response.json()["data"]
                reply_msg = await message.reply(
                    f"🔑 Лимит: {data['limit'] or '∞'} | Использовано: {data['usage']}\n"
                    f"Тип ключа: {'Бесплатный' if data['is_free_tier'] else 'Платный'}"
                )
                save_message(reply_msg)
            else:
                reply_msg = await message.reply(f"⚠️ Ошибка получения лимита: {response.status_code}")
                save_message(reply_msg)
        except Exception as e:
            reply_msg = await message.reply(f"❌ Ошибка: {e}")
            save_message(reply_msg)
        return

    reply_msg = await message.reply("Неизвестная команда. Используй k menu для списка.")
    save_message(reply_msg)

# Генерация ответа
async def generate_reply(prompt: str) -> str:
    global current_key_index

    def try_request(api_key):
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": BOT_PERSONA},
                *[
                    {
                        "role": "assistant" if author == "Botyan" else "user",
                        "content": content
                    } for author, content in get_last_messages(100)
                ],
                {"role": "user", "content": prompt}
            ]
        }
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            if response.status_code == 429:
                return "RATE_LIMITED"
            if response.status_code == 401:
                return "UNAUTHORIZED"
            if response.status_code == 403:
                return "FORBIDDEN"
            if response.status_code >= 500:
                return "SERVER_ERROR"
            data = response.json()
            if data.get("choices"):
                return data["choices"][0]["message"]["content"].strip()
            else:
                return "🤖 [Модель не вернула ответа]"
        except Exception as e:
            return f"⚠️ Ошибка подключения: {e}"

    for _ in range(len(OPENROUTER_API_KEYS)):
        key = OPENROUTER_API_KEYS[current_key_index]
        reply = await asyncio.to_thread(try_request, key)
        if reply in ["RATE_LIMITED", "UNAUTHORIZED", "FORBIDDEN", "SERVER_ERROR"]:
            current_key_index = (current_key_index + 1) % len(OPENROUTER_API_KEYS)
            await asyncio.sleep(1)
            continue
        else:
            return reply
    return "🚫 Все API-ключи временно недоступны. Попробуй позже."

async def start_telegram_bot():
    me = await bot.get_me()
    dp.include_router(router)
    print(f"✅ Бот @{me.username} запущен!")
    await dp.start_polling(bot, timeout=60)