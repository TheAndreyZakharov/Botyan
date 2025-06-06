import discord
from discord.ext import commands

class HelpMenu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="меню", aliases=["помощь"])
    async def меню(self, ctx):
        embed = discord.Embed(
            title="📜 Команды бота",
            description="Вот что я умею. Используй с умом (или без него):",
            color=discord.Color.dark_gold()
        )

        embed.add_field(
            name="💬 Общение",
            value=(
                "• Просто упомяни меня, и я отвечу.\n"
                "• Или ответь на моё сообщение — я продолжу беседу.\n"
                "• Иногда сам вмешиваюсь в разговор 😉"
            ),
            inline=False
        )

        embed.add_field(
            name="🎰 Казино",
            value="`!баланс` — твой счёт\n`!крутить [ставка]` — слот-машина на удачу",
            inline=False
        )

        embed.add_field(
            name="🖼️ Демотиватор",
            value="`!демотиватор` — прикрепи изображение или ответь на сообщение с ним",
            inline=False
        )

        embed.add_field(
            name="🧠 Автосообщения",
            value="Я сам пишу что-то умное раз в час. Или глупое. Или странное.",
            inline=False
        )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpMenu(bot))
