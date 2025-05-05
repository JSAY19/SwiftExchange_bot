import asyncio
import logging
from aiogram import Bot, Dispatcher
from src.config.config import BOT_TOKEN
from src.bot.handlers.commands import router

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Функция конфигурации и запуска бота
async def main():
    # Создаем объекты бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Регистрируем роутеры
    dp.include_router(router)

    # Пропускаем накопившиеся апдейты и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
