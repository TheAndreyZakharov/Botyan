import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import discord
from discord.ext import commands
import random
import requests
import asyncio
import re
from config import (
    BOT_TOKEN, OPENROUTER_API_KEYS, OPENROUTER_MODEL,
    BOT_PERSONA, BOT_AUTO_PROMPT, BOT_INTERJECT_TEMPLATE,
    ALLOWED_DS_GUILD_ID, ALLOWED_DS_USER_ID
)
from discord_bot.core.message_log import save_message, get_last_messages

current_key_index = 0

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

AVAILABLE_REACTIONS = [
    "😂", "🤣", "😄", "😊", "❤️", "🔥", "👍", "😍", "🥳", "😎", "✨", "💯", "🤝",
    "😮", "🤔", "😐", "🙃", "🤨", "🧐", "👀", "😶", "😬", "😑", "📌", "👆",
    "👎", "😢", "😡", "💔", "🤯", "😤", "⚡", "🙄", "😠", "🖕", "💩", "❗", "❓",
    "😜", "😱", "🥲", "🤗", "😘", "🤬", "😭", "😏", "🥺", "😅", "😆", "😈", "💋",
    "🍒", "🍌", "🍓", "🥒", "🍑", "🍆"
]

def clean_mentions(text):
    return re.sub(r"<@!?\d+>|<@&\d+>", "", text).strip()

def is_ds_allowed(message):
    # ЛС — только определённые пользователи
    if isinstance(message.channel, discord.DMChannel):
        return message.author.id in ALLOWED_DS_USER_ID
    # Сервер — только разрешённый сервер
    if message.guild is None:
        return False
    return message.guild.id == ALLOWED_DS_GUILD_ID

async def handle_not_allowed(message):
    if isinstance(message.channel, discord.DMChannel):
        await message.channel.send("Я не хочу общаться лично с тобой! До свидания 👋")
    else:
        await message.channel.send("Я не собираюсь участвовать в этом чате! До свидания 👋")

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
                        "role": "assistant" if author == bot.user.name else "user",
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
        except requests.exceptions.Timeout:
            return "TIMEOUT"
        except Exception as e:
            return f"⚠️ Ошибка подключения: {e}"

    for _ in range(len(OPENROUTER_API_KEYS)):
        key = OPENROUTER_API_KEYS[current_key_index]
        reply = await asyncio.to_thread(try_request, key)
        if reply in ["RATE_LIMITED", "UNAUTHORIZED", "FORBIDDEN", "SERVER_ERROR", "TIMEOUT"]:
            current_key_index = (current_key_index + 1) % len(OPENROUTER_API_KEYS)
            await asyncio.sleep(1)
            continue
        else:
            return reply

    return "🚫 Все API-ключи временно недоступны. Попробуй позже."

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} запущен!")

@bot.event
async def on_message(message):
    # 1. Сразу фильтр доступа:
    if not is_ds_allowed(message):
        await handle_not_allowed(message)
        return
    if message.author == bot.user:
        return

    save_message(message)

    # Обычное обращение к боту 
    is_directed = False
    prompt = ""

    # Через упоминание
    if bot.user.mentioned_in(message):
        is_directed = True
        prompt = clean_mentions(message.content.replace(f"<@{bot.user.id}>", "")).strip()

    # Через reply
    elif message.reference:
        try:
            replied_msg = await message.channel.fetch_message(message.reference.message_id)
            if replied_msg.author == bot.user:
                is_directed = True
                prompt = message.content.strip()
        except Exception:
            pass

    # Ответ на обращение
    if is_directed and prompt:
        await message.channel.typing()
        reply = await generate_reply(prompt)
        if reply.strip():
            sent_msg = await message.channel.send(reply)
            # Просто рандомная реакция от бота:
            try:
                await sent_msg.add_reaction(random.choice(AVAILABLE_REACTIONS))
            except Exception:
                pass

    # Иногда случайный автокоммент
    elif not message.author.bot and random.randint(1, 7) == 1:
        await asyncio.sleep(random.randint(2, 5))
        await message.channel.typing()
        history_text = "\n".join(f"{author}: {content}" for author, content in get_last_messages(100))
        context_prompt = BOT_INTERJECT_TEMPLATE.format(
            text=message.content,
            persona=BOT_PERSONA,
            history=history_text
        )
        reply = await generate_reply(context_prompt)
        if reply.strip():
            sent_msg = await message.channel.send(reply)
            try:
                await sent_msg.add_reaction(random.choice(AVAILABLE_REACTIONS))
            except Exception:
                pass

    # Иногда рандомная реакция на любое сообщение
    if not message.author.bot and random.randint(1, 10) == 1:
        try:
            await message.add_reaction(random.choice(AVAILABLE_REACTIONS))
        except Exception:
            pass

    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    if not is_ds_allowed(ctx.message):
        await handle_not_allowed(ctx.message)
        return
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Неизвестная команда. Напиши `!меню` для справки.")
    else:
        raise error

@bot.command()
async def тест(ctx):
    if not is_ds_allowed(ctx.message):
        await handle_not_allowed(ctx.message)
        return
    reply = await generate_reply("Привет! Как дела?")
    await ctx.send(reply or "⚠️ Пусто")

@bot.command()
async def лимит(ctx):
    if not is_ds_allowed(ctx.message):
        await handle_not_allowed(ctx.message)
        return
    try:
        key = OPENROUTER_API_KEYS[current_key_index]
        headers = {"Authorization": f"Bearer {key}"}
        response = requests.get("https://openrouter.ai/api/v1/auth/key", headers=headers)
        if response.ok:
            data = response.json()["data"]
            await ctx.send(
                f"🔑 Лимит: {data['limit'] or '∞'} | Использовано: {data['usage']}\n"
                f"Тип ключа: {'Бесплатный' if data['is_free_tier'] else 'Платный'}"
            )
        else:
            await ctx.send(f"⚠️ Ошибка получения лимита: {response.status_code}")
    except Exception as e:
        await ctx.send(f"❌ Ошибка: {e}")

async def start_discord_bot():
    await bot.start(BOT_TOKEN)
