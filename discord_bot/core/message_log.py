import json
import os
from datetime import datetime

DB_FILE = "data/messages.json"
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

def save_message(message):
    if not message.content.strip():
        return

    messages = load_messages()

    # Проверка дубликатов
    if any(str(msg["message_id"]) == str(message.id) for msg in messages):
        return

    entry = {
        "message_id": str(message.id),
        "user": message.author.display_name,
        "content": message.content,
        "timestamp": message.created_at.isoformat()
    }

    messages.append(entry)
    save_messages(messages)
    enforce_db_size_limit()

def enforce_db_size_limit():
    if os.path.exists(DB_FILE) and (os.path.getsize(DB_FILE) / (1024 * 1024)) > MAX_DB_SIZE_MB:
        messages = load_messages()
        # Удалим первые 100 сообщений
        trimmed = messages[-(len(messages) - 100):]
        save_messages(trimmed)

def get_last_messages(limit=50):
    messages = load_messages()
    return [(m["user"], m["content"]) for m in messages[-limit:]]

# Вызывается при старте, если файл пустой
async def populate_from_channel(channel):
    print(f"🔄 Сканируем историю канала: {channel.name} ({channel.id})")
    messages = []
    async for message in channel.history(limit=None, oldest_first=True):
        if message.content.strip():
            messages.append({
                "message_id": str(message.id),
                "user": message.author.display_name,
                "content": message.content,
                "timestamp": message.created_at.isoformat()
            })
    save_messages(messages)
    print(f"✅ Сканирование завершено. Загружено {len(messages)} сообщений.")
