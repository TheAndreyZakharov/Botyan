import asyncio
import signal

from discord_bot.bot import start_discord_bot
from telegram_bot.bot import start_telegram_bot

async def main():
    tg_task = asyncio.create_task(start_telegram_bot())
    ds_task = asyncio.create_task(start_discord_bot())

    print("Оба бота запущены. Для остановки — Ctrl+C")

    # Ждём Ctrl+C
    stop_event = asyncio.Event()

    def stop(*_):
        print("\nОстановка... Ждём завершения процессов.")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop)

    await stop_event.wait()

    tg_task.cancel()
    ds_task.cancel()
    await asyncio.gather(tg_task, ds_task, return_exceptions=True)
    print("Все боты остановлены корректно.")

if __name__ == "__main__":
    asyncio.run(main())
