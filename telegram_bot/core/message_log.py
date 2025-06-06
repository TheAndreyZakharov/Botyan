import json
import os
from datetime import datetime
from aiogram.types import Message
from aiogram import Bot

DB_FILE = "data/tg_messages.json"
MAX_DB_SIZE_MB = 100
MAX_TOTAL_MESSAGES = 10_000

def load_messages():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_messages(messages):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(messages[-MAX_TOTAL_MESSAGES:], f, ensure_ascii=False, indent=2)

def save_message(message: Message):
    text = getattr(message, "text", None) or ""
    user_obj = getattr(message, "from_user", None)
    if user_obj is not None:
        user_name = getattr(user_obj, "full_name", None) or getattr(user_obj, "username", None) or str(user_obj.id)
        is_bot = getattr(user_obj, "is_bot", False)
        user_id = getattr(user_obj, "id", None)
    else:
        user_name = "unknown"
        is_bot = False
        user_id = None

    # Сохраняем file_id для фото, если есть
    photo_file_id = None
    if getattr(message, "photo", None):
        # Берём самое большое по размеру (последний элемент списка)
        photo_file_id = message.photo[-1].file_id

    messages = load_messages()
    if any(str(msg["message_id"]) == str(message.message_id) for msg in messages):
        return

    entry = {
        "message_id": str(message.message_id),
        "user": user_name,
        "user_id": user_id,
        "is_bot": is_bot,
        "content": text,
        "timestamp": getattr(message, "date", datetime.utcnow()).isoformat(),
        "chat_id": getattr(getattr(message, "chat", None), "id", None),
        "chat_type": getattr(getattr(message, "chat", None), "type", None),
        "photo_file_id": photo_file_id,
    }
    messages.append(entry)
    save_messages(messages)
    enforce_db_size_limit()


def enforce_db_size_limit():
    if os.path.exists(DB_FILE) and (os.path.getsize(DB_FILE) / (1024 * 1024)) > MAX_DB_SIZE_MB:
        messages = load_messages()
        trimmed = messages[-(len(messages) - 100):]
        save_messages(trimmed)

def get_last_messages(limit=50):
    messages = load_messages()
    return [(m["user"], m["content"]) for m in messages[-limit:]]

async def populate_from_chat_history(bot: Bot, chat_id: int, min_id: int = 1, progress_callback=None):
    """
    Скачивает максимум истории чата (по возможности), добавляет все новые сообщения в базу, не дублируя.
    Можно вызывать в on_startup или отдельно по команде.
    """
    from aiogram.exceptions import TelegramAPIError

    messages_db = {m["message_id"]: m for m in load_messages()}

    batch_size = 100  # Больше Telegram не даёт
    offset_id = 0
    total_added = 0
    last_id = 0
    while True:
        try:
            history = await bot.get_chat_history(chat_id, limit=batch_size, offset_id=offset_id)
        except TelegramAPIError as e:
            print(f"[populate_from_chat_history] Ошибка Telegram: {e}")
            break

        if not history or len(history) == 0:
            break

        for msg in history:
            if msg.message_id in messages_db:
                continue
            # ищем file_id если есть фото
            photo_file_id = None
            if getattr(msg, "photo", None):
                photo_file_id = msg.photo[-1].file_id

            entry = {
                "message_id": str(msg.message_id),
                "user": getattr(msg.from_user, "full_name", None) or getattr(msg.from_user, "username", None) if msg.from_user else "unknown",
                "user_id": getattr(msg.from_user, "id", None) if msg.from_user else None,
                "is_bot": getattr(msg.from_user, "is_bot", False) if msg.from_user else False,
                "content": getattr(msg, "text", None) or "",
                "timestamp": getattr(msg, "date", datetime.utcnow()).isoformat(),
                "chat_id": getattr(msg.chat, "id", None),
                "chat_type": getattr(msg.chat, "type", None),
                "photo_file_id": photo_file_id,
            }
            messages_db[msg.message_id] = entry
            total_added += 1
            last_id = msg.message_id
        if progress_callback:
            await progress_callback(total_added, last_id)

        # Если дошли до самого старого сообщения
        if len(history) < batch_size:
            break
        offset_id = history[-1].message_id

    # Сохраняем всё
    messages = list(sorted(messages_db.values(), key=lambda m: int(m["message_id"])))
    save_messages(messages)
    enforce_db_size_limit()
    print(f"[populate_from_chat_history] Готово! Добавлено {total_added} новых сообщений.")
