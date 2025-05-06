from aiogram import Router, types, F
from aiogram.filters import Command
from src.bot.keyboards.reply_keyboards import get_main_keyboard
from src.bot.keyboards.inline_keyboards import get_exchange_main_keyboard, get_usdt_directions_keyboard, get_exchange_type_keyboard
from datetime import datetime, timedelta
import asyncio
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
import logging
from .colors_logs import *
from .colors_logs import get_user_display

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    try:
        logging.info(f"User {get_user_display(message.from_user)} /start.")
        # Яркое изображение
        output_path = "pictures/XchangerBot_bright.png"
        photo = FSInputFile(output_path)
        await message.answer_photo(
            photo=photo,
            caption="🏦 Мы предлагаем надёжные, оперативные и полностью автоматизированные услуги обмена российских рублей, USDT, THB.\n" 
                    "💎 Приоритет №1 — качество нашего сервиса. Мы высоко ценим каждого нашего клиента и стремимся сделать процесс обмена максимально удобным и быстрым, чтобы Вы всегда возвращались к нам.\n"
                    "💬 → Техническая поддержка: @...",
            reply_markup=get_main_keyboard()
        ) 
    except FileNotFoundError:
        logging.error(f"Не найден файл изображения {output_path}")
        await message.answer("Извините, произошла ошибка при загрузке изображения. Команда уведомлена.")
    except Exception as e:
        logging.error(f"Ошибка в cmd_start: {str(e)}")
        await message.answer("Извините, произошла ошибка. Попробуйте позже или обратитесь в поддержку.")


@router.message(F.text == "💰 Совершить обмен")
async def exchange_main(message: types.Message):
    try:
        logging.info(f"User '{get_user_display(message.from_user)}' выбрал 'Совершить обмен'.")
        await message.answer(
            "Выберите валюту, которую вы желаете получить:",
            reply_markup=get_exchange_main_keyboard()
        )
    except Exception as e:
        logging.error(f"Ошибка в exchange_main: {str(e)}")
        await message.answer("Извините, произошла ошибка. Попробуйте позже или обратитесь в поддержку.")

@router.callback_query(F.data == "exchange_main")
async def exchange_main_back(callback_query: types.CallbackQuery):
    try:
        logging.info(f"User '{get_user_display(callback_query.from_user)}' вернулся в главное меню.")
        await callback_query.message.edit_text(
            "Выберите валюту, которую вы желаете получить:",
            reply_markup=get_exchange_main_keyboard()
        )
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Ошибка в exchange_main_back: {str(e)}")
        try:
            await callback_query.answer("Произошла ошибка. Попробуйте снова.")
        except:
            logging.error("Не удалось отправить ответ на callback_query")


@router.callback_query(F.data == "exchange_usdt")
async def exchange_usdt(callback_query: types.CallbackQuery):
    try:
        logging.info(f"User '{get_user_display(callback_query.from_user)}' выбрал обмен USDT.")
        await callback_query.message.edit_text(
            "THB\nВыберите направление обмена:",
            reply_markup=get_usdt_directions_keyboard()
        )
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Ошибка в exchange_usdt: {str(e)}")
        try:
            await callback_query.answer("Произошла ошибка. Попробуйте снова.")
        except:
            logging.error("Не удалось отправить ответ на callback_query")

@router.callback_query(F.data == "usdt_to_thb")
async def usdt_to_thb(callback_query: types.CallbackQuery):
    try:
        logging.info(f"User '{get_user_display(callback_query.from_user)}' выбрал USDT → THB.")
        await callback_query.message.edit_text(
            "<b>Выбор обмена</b>\n\n"
            "<b>Варианты обмена:</b>\n\n"
            "🌐 <b>В банкомате</b>, описание обмена\n"
            "мин. сумма: 🎉✨✨\n"
            "макс. сумма: 🎉✨✨\n\n"
            "🏢 <b>Офлайн</b>, описание обмена\n"
            "мин. сумма: 🎉✨✨\n"
            "макс. сумма: 🎉✨✨",
            reply_markup=get_exchange_type_keyboard(),
            parse_mode="HTML"
        )
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Ошибка в usdt_to_thb: {str(e)}")
        try:
            await callback_query.answer("Произошла ошибка. Попробуйте снова.")
        except:
            logging.error("Не удалось отправить ответ на callback_query")