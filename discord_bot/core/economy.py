import discord
from discord.ext import commands, tasks
import random
import asyncio
import json
import os

DATA_FILE = "data/economy_data.json"
START_BALANCE = 100_000

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
    if str_id not in data:
        data[str_id] = {"balance": START_BALANCE}
        save_data(data)

def get_balance(user_id: int) -> int:
    ensure_user_exists(user_id)
    data = load_data()
    return data[str(user_id)]["balance"]

def update_balance(user_id: int, amount: int):
    ensure_user_exists(user_id)
    data = load_data()
    data[str(user_id)]["balance"] += amount
    save_data(data)

def bulk_ensure_users(users: list[discord.User]):
    data = load_data()
    changed = False
    for user in users:
        str_id = str(user.id)
        if str_id not in data and not user.bot:
            data[str_id] = {"balance": START_BALANCE}
            changed = True
    if changed:
        save_data(data)


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_new_members.start()

    def cog_unload(self):
        self.check_new_members.cancel()

    @tasks.loop(hours=1)
    async def check_new_members(self):
        for guild in self.bot.guilds:
            bulk_ensure_users(guild.members)

    @check_new_members.before_loop
    async def before_check_new_members(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            bulk_ensure_users(guild.members)
        print("✅ Экономика инициализирована для всех участников.")

    @commands.command(name="баланс")
    async def баланс(self, ctx):
        balance = get_balance(ctx.author.id)
        await ctx.send(f"💰 {ctx.author.mention}, у тебя на счету **{balance}** монет.")

    @commands.command(name="крутить")
    async def крутить(self, ctx, ставка: int = None):
        if ставка is None:
            await ctx.send("❗ Укажи сумму ставки, например `!крутить 500`")
            return
        if ставка <= 0:
            await ctx.send("❗ Ставка должна быть положительной.")
            return

        баланс = get_balance(ctx.author.id)
        if ставка > баланс:
            await ctx.send("❌ У тебя недостаточно монет.")
            return

        message = await ctx.send("🎰 Вращаем барабаны...")

        for _ in range(4):
            случайные = [random.choice(SLOTS)[0] for _ in range(3)]
            await message.edit(content=" ".join(случайные))
            await asyncio.sleep(0.1)

        итоговые = [random.choice(SLOTS) for _ in range(3)]
        символы = [item[0] for item in итоговые]
        await message.edit(content=" ".join(символы))

        if символы[0] == символы[1] == символы[2]:
            коэффициент = итоговые[0][1]
            выигрыш = ставка * коэффициент
            update_balance(ctx.author.id, выигрыш)
            текст = f"🎉 {ctx.author.mention}, ты выиграл **{выигрыш}** монет! (`x{коэффициент}`)"
        else:
            update_balance(ctx.author.id, -ставка)
            текст = f"😢 {ctx.author.mention}, не повезло. Потеряно **{ставка}** монет."

        await asyncio.sleep(0.4)
        await message.edit(content=f"{' '.join(символы)}\n\n{текст}")

async def setup(bot):
    await bot.add_cog(Economy(bot))
