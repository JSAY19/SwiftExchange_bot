import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher
from decouple import config  # Убедитесь, что у вас есть .env файл с BOT_TOKEN
from aiogram.exceptions import TelegramNetworkError

# Импортируем router из вашего файла с хендлерами
# ИЗМЕНИТЕ 'src.bot.handlers.user_handlers' на актуальный путь к файлу,
# где определен ваш основной router и глобальные переменные для сессии/клиента.
# Например, если ваш router в src.bot.handlers.commands, то:
# from src.bot.handlers.commands import router, aiohttp_session_global, coingecko_client_global
# Но лучше, чтобы глобальные переменные были в том же модуле, что и router, который их использует.
# Или передавать их через workflow_data диспетчера.

# Предположим, что ваш основной router и глобальные переменные
# aiohttp_session_global, coingecko_client_global
# определены в модуле src.bot.handlers.user_handlers
import src.bot.handlers.commands as user_handlers_module  # ИМПОРТИРУЕМ МОДУЛЬ

# Импортируем CoinGeckoClient
from src.services.CoinGecko import CoinGeckoClient  # Убедитесь, что путь верный

# Включаем логирование
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# --- Функции для управления жизненным циклом сессии и клиента ---
async def on_startup(bot: Bot, dispatcher: Dispatcher):  # dispatcher передается автоматически Aiogram 3.x
    logging.info("Bot startup process initiated...")
    # Создаем сессию и клиент и присваиваем их глобальным переменным в импортированном модуле
    try:
        user_handlers_module.aiohttp_session_global = aiohttp.ClientSession()
        user_handlers_module.coingecko_client_global = CoinGeckoClient(
            session=user_handlers_module.aiohttp_session_global)
        logging.info("Aiohttp session and CoinGeckoClient initialized successfully.")
    except Exception as e:
        logging.error(f"Error during on_startup (aiohttp/CoinGeckoClient initialization): {e}")
        # Решите, что делать дальше: остановить бота или работать без CoinGecko
        # Например, можно выбросить исключение, чтобы бот не запустился без критичного компонента
        # raise RuntimeError("Failed to initialize CoinGecko client.") from e


async def on_shutdown(bot: Bot, dispatcher: Dispatcher):
    logging.info("Bot shutdown process initiated...")
    if user_handlers_module.aiohttp_session_global and not user_handlers_module.aiohttp_session_global.closed:
        try:
            await user_handlers_module.aiohttp_session_global.close()
            logging.info("Aiohttp session closed successfully.")
        except Exception as e:
            logging.error(f"Error during aiohttp session close: {e}")
    else:
        logging.info("Aiohttp session was not initialized or already closed.")


# --- Функция конфигурации и запуска бота ---
async def main():
    bot_token = config('BOT_TOKEN', default=None)
    if not bot_token:
        logging.error("BOT_TOKEN не найден в конфигурации! Завершение работы.")
        return

    # Создаем объекты бота и диспетчера
    bot = Bot(token=bot_token)
    dp = Dispatcher()  # По умолчанию storage=MemoryStorage()

    # Регистрируем обработчики startup и shutdown
    # Эти функции будут вызваны при запуске и остановке polling'а
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Регистрируем роутеры
    # Предполагаем, что ваш основной router находится в user_handlers_module.router
    dp.include_router(user_handlers_module.router)
    logging.info("Routers included.")

    # Пропускаем накопившиеся апдейты перед запуском polling'а
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logging.info("Pending updates dropped.")
    except Exception as e:
        logging.warning(f"Could not delete webhook (maybe bot is not using it or no rights): {e}")

    # Запускаем polling с обработкой ошибок и повторными попытками
    retry_count = 0
    max_retries = 10  # Максимальное количество последовательных быстрых ретраев
    base_retry_timeout = 5  # Начальный таймаут в секундах
    current_retry_timeout = base_retry_timeout

    logging.info("Starting bot polling...")
    while True:
        try:
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
            # Если start_polling завершился без исключения (например, по команде остановки), выходим из цикла
            logging.info("Polling stopped gracefully.")
            break
        except TelegramNetworkError as e:
            retry_count += 1
            logging.error(f"Telegram Network Error: {e}. Attempt {retry_count} of {max_retries} (fast retries).")

            if retry_count >= max_retries:
                # После max_retries быстрых попыток, увеличиваем таймаут значительно
                current_retry_timeout = min(current_retry_timeout * 2, 90)  # Удваиваем, но не более 90с
                logging.warning(f"Max fast retries reached. Increased retry timeout to {current_retry_timeout}s.")
                retry_count = 0  # Сбрасываем счетчик быстрых ретраев

            logging.info(f"Retrying connection in {current_retry_timeout} seconds...")
            await asyncio.sleep(current_retry_timeout)
        except Exception as e:
            # Для всех других неожиданных ошибок
            logging.exception("An unexpected error occurred during polling:")  # logging.exception включает traceback
            current_retry_timeout = min(current_retry_timeout * 1.5, 120)  # Увеличиваем таймаут, но не так агрессивно
            logging.info(f"Retrying after unexpected error in {current_retry_timeout} seconds...")
            await asyncio.sleep(current_retry_timeout)
        else:
            logging.info("Polling was interrupted without an error that requires retry.")
            break


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by KeyboardInterrupt.")
    except Exception as e:
        logging.critical(f"Critical error in main execution: {e}", exc_info=True)