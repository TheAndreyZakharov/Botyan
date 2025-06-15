import json
import os
import random
from config import STANDARD_SETS

STICKER_MEM_FILE = "data/sticker_memory.json"

def load_sticker_memory():
    if os.path.exists(STICKER_MEM_FILE):
        with open(STICKER_MEM_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}  # Возвращаем пустой dict, если файл пустой
            return json.loads(content)
    return {}


def save_sticker_memory(mem):
    with open(STICKER_MEM_FILE, "w", encoding="utf-8") as f:
        json.dump(mem, f, ensure_ascii=False, indent=2)

def add_sticker_to_memory(chat_id: int, sticker_file_id: str, set_name: str = None):
    """
    Сохраняет info о стикере, чтобы потом можно было отправлять рандомные стикеры из тех, что реально были в чате.
    """
    mem = load_sticker_memory()
    str_id = str(chat_id)
    if str_id not in mem:
        mem[str_id] = []
    if not any(s["file_id"] == sticker_file_id for s in mem[str_id]):
        mem[str_id].append({"file_id": sticker_file_id, "set_name": set_name})
        save_sticker_memory(mem)

def get_all_stickers_for_chat(chat_id: int):
    mem = load_sticker_memory()
    str_id = str(chat_id)
    if str_id not in mem:
        return []
    return mem[str_id]

def get_used_set_names(chat_id: int):
    """
    Возвращает все стикерпакеты, которые были реально использованы в чате (set_name)
    """
    all_stickers = get_all_stickers_for_chat(chat_id)
    set_names = set()
    for s in all_stickers:
        if s.get("set_name"):
            set_names.add(s["set_name"])
    return list(set_names)

def get_random_sticker(bot, chat_id: int):
    """
    Рандомно выбирает sticker_file_id из:
    - часто используемых в чате stickerpack (80% шанс)
    - стандартных stickerpack (20% шанс)
    Если нет вообще никакого варианта — вернет None.
    """
    stickers = get_all_stickers_for_chat(chat_id)
    from aiogram import types

    # 80% шанс — из чата
    if stickers and random.random() < 0.8:
        # отбираем file_id только из стандартных или реально юзанных сетов
        used_set_names = get_used_set_names(chat_id)
        good_set_names = set(STANDARD_SETS) | set(used_set_names)
        good_stickers = [s for s in stickers if s.get("set_name") in good_set_names]
        if good_stickers:
            return random.choice(good_stickers)["file_id"]
        else:
            # если из чата ничего подходящего — пробуем стандартные ниже
            pass

    # 20% шанс — случайно из стандартных пакетов (или fallback)
    # Мы НЕ знаем заранее file_id, поэтому нужен любой chat/user, у кого этот стикерпак уже использовался.
    # fallback: возвращаем любой стикер из стандартных пакетов, если встречался хотя бы раз в этом чате
    standard_stickers = [s for s in stickers if s.get("set_name") in STANDARD_SETS]
    if standard_stickers:
        return random.choice(standard_stickers)["file_id"]

    # Вариант: если совсем ничего — None
    return None

def get_sticker_stats(chat_id: int):
    """
    Возвращает частоты по set_name — показывает, какие паки чаще всего юзали в чате.
    """
    stickers = get_all_stickers_for_chat(chat_id)
    stats = {}
    for s in stickers:
        set_name = s.get("set_name") or "unknown"
        stats[set_name] = stats.get(set_name, 0) + 1
    return stats

def get_standard_sets():
    """Вернуть список стандартных стикерпаков"""
    return STANDARD_SETS
