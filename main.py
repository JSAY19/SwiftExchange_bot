import asyncio
import logging
from aiogram import Bot, Dispatcher
from src.config.config import BOT_TOKEN
from src.bot.handlers.commands import router
import time
from aiogram.exceptions import TelegramNetworkError

# Включаем логирование
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Функция конфигурации и запуска бота
async def main():
    # Создаем объекты бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Регистрируем роутеры
    dp.include_router(router)

    # Пропускаем накопившиеся апдейты
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем polling с обработкой ошибок и повторными попытками
    retry_count = 0
    max_retries = 10
    retry_timeout = 5
    
    while True:
        try:
            logging.info("Запуск бота...")
            await dp.start_polling(bot)
        except TelegramNetworkError as e:
            retry_count += 1
            logging.error(f"Ошибка сети Telegram: {e}. Попытка {retry_count} из {max_retries}")
            
            if retry_count >= max_retries:
                retry_count = 0
                logging.warning(f"Достигнуто максимальное количество попыток. Сброс счетчика и увеличение таймаута.")
                retry_timeout = min(retry_timeout * 2, 90)  # Увеличиваем таймаут, но не более 5 минут
            
            logging.info(f"Повторное подключение через {retry_timeout} секунд...")
            await asyncio.sleep(retry_timeout)
        except Exception as e:
            logging.error(f"Неожиданная ошибка: {e}")
            retry_timeout = min(retry_timeout * 2, 90)
            logging.info(f"Повторное подключение через {retry_timeout} секунд...")
            await asyncio.sleep(retry_timeout)

if __name__ == "__main__":
    asyncio.run(main())
