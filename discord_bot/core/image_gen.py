import discord
from discord.ext import commands
import requests
from PIL import Image, ImageDraw, ImageFont
import io
import os
from config import OPENROUTER_API_KEYS, OPENROUTER_MODEL, BOT_PERSONA, DEMOTIVATOR_PROMPT_TEMPLATE
from discord_bot.core.message_log import get_last_messages
import textwrap
import asyncio
import re

current_key_index = 0

async def generate_caption_from_chat(history: list[str]) -> str:
    global current_key_index

    all_messages = get_last_messages(1000)
    filtered_history = [
        (user, content) for user, content in all_messages
        if not content.strip().startswith("!")
    ]

    formatted_history = "\n".join(f"- {user}: {content}" for user, content in filtered_history)

    full_prompt = DEMOTIVATOR_PROMPT_TEMPLATE.format(
        persona=BOT_PERSONA,
        history=formatted_history
    )

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": BOT_PERSONA},
            {"role": "user", "content": full_prompt}
        ]
    }

    def try_request(api_key):
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
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
            if response.status_code >= 400:
                return f"[⚠️] Ошибка: {response.status_code}"
            data = response.json()
            # print(f"[📨] Ответ от OpenRouter: {response.status_code} — {response.text}")
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[⚠️] Исключение при генерации подписи: {e}")
            return "Ошибка генерации подписи."


    for _ in range(len(OPENROUTER_API_KEYS)):
        key = OPENROUTER_API_KEYS[current_key_index]
        result = await asyncio.to_thread(try_request, key)

        if result == "RATE_LIMITED":
            current_key_index = (current_key_index + 1) % len(OPENROUTER_API_KEYS)
            await asyncio.sleep(1)
            continue
        else:
            return result

    return "🚫 Все API-ключи перегружены. Подожди немного."


def wrap_text(draw, text, font, max_width):
    """Разбивает текст на строки, чтобы каждая влезала в заданную ширину"""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test_line = current + " " + word if current else word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            current = test_line
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

def create_demotivator(image_bytes, caption: str) -> io.BytesIO:
    target_size = (600, 400)
    total_width = 640
    total_height = 700

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize(target_size)

    canvas = Image.new("RGB", (total_width, total_height), "black")
    draw = ImageDraw.Draw(canvas)

    photo_x = (total_width - target_size[0]) // 2
    photo_y = 40
    frame_rect = [photo_x - 2, photo_y - 2, photo_x + target_size[0] + 2, photo_y + target_size[1] + 2]
    draw.rectangle(frame_rect, outline="white", width=4)
    canvas.paste(img, (photo_x, photo_y))

    font_path = os.path.join("fonts", "timesnewromanpsmt.ttf")
    try:
        font_title = ImageFont.truetype(font_path, 36)
    except Exception as e:
        print(f"[⚠️] Шрифт не найден или не загрузился: {e}")
        font_title = ImageFont.load_default()

    # Убираем markdown и префиксы типа "1.", "2.", кавычки и лишние пробелы
    clean_caption = re.sub(r"[*_~`>\"]", "", caption)
    lines = clean_caption.strip().split("\n")

    # Убираем нумерацию типа "1. ..." или "2. ..." и чистим строки
    stripped_lines = []
    for line in lines:
        line = line.strip()
        line = re.sub(r"^\d+\.\s*", "", line)  # удаляет "1. " или "2. "
        if line:
            stripped_lines.append(line)

    wrapped_lines = []
    for line in stripped_lines[:2]:  # берём только максимум 2 логические строки
        wrapped = wrap_text(draw, line, font_title, max_width=580)
        wrapped_lines.extend(wrapped)

    # Ограничим максимальное количество строк (например, 4)
    wrapped_lines = wrapped_lines[:4]

    text_y = photo_y + target_size[1] + 30
    for i, line in enumerate(wrapped_lines):
        bbox = draw.textbbox((0, 0), line, font=font_title)
        w = bbox[2] - bbox[0]
        x = (total_width - w) // 2
        draw.text((x, text_y + i * 45), line, font=font_title, fill="white")

    output = io.BytesIO()
    canvas.save(output, format="PNG")
    output.seek(0)
    return output


class Demotivator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="демотиватор")
    async def демотиватор(self, ctx):
        image_bytes = None

        # Вложение
        if ctx.message.attachments:
            url = ctx.message.attachments[0].url
            image_bytes = requests.get(url).content

        # Или ответ на сообщение
        elif ctx.message.reference:
            replied_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if replied_msg.attachments:
                url = replied_msg.attachments[0].url
                image_bytes = requests.get(url).content

        if not image_bytes:
            await ctx.send("📎 Прикрепи изображение или ответь на сообщение с ним.")
            return

        await ctx.send("Делаю...")

        caption = await generate_caption_from_chat([])
        result = create_demotivator(image_bytes, caption)

        await ctx.send(file=discord.File(result, filename="demotivator.png"))

async def setup(bot):
    await bot.add_cog(Demotivator(bot))
