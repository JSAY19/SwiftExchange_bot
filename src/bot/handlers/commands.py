from aiogram import Router, types, F
from aiogram.filters import Command
from src.bot.keyboards.reply_keyboards import get_main_keyboard
from src.bot.keyboards.inline_keyboards import get_exchange_main_keyboard, get_rub_directions_keyboard, get_thb_directions_keyboard, get_usdt_directions_keyboard
from datetime import datetime, timedelta
import asyncio
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
import logging
from .colors_logs import *
from PIL import Image, ImageEnhance
from .colors_logs import get_user_display
router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
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


@router.message(lambda message: message.text == "💰 Совершить обмен")
async def exchange_main(message: types.Message):
    logging.info(f"User '{get_user_display(message.from_user)}' выбрал 'Совершить обмен'.")
    await message.answer(
        "Выберите валюту, которую вы желаете получить:",
        reply_markup=get_exchange_main_keyboard()
    )

@router.callback_query(lambda c: c.data == "exchange_main")
async def exchange_main_back(callback_query: types.CallbackQuery):
    logging.info(f"User '{get_user_display(callback_query.from_user)}' вернулся в главное меню.")
    await callback_query.message.edit_text(
        "Выберите валюту, которую вы желаете получить:",
        reply_markup=get_exchange_main_keyboard()
    )

@router.callback_query(lambda c: c.data == "exchange_rub")
async def exchange_rub(callback_query: types.CallbackQuery):
    logging.info(f"User '{get_user_display(callback_query.from_user)}' выбрал обмен RUB.")
    await callback_query.message.edit_text(
        "RUB\nВыберите направление обмена:",
        reply_markup=get_rub_directions_keyboard()
    )

@router.callback_query(lambda c: c.data == "exchange_thb")
async def exchange_thb(callback_query: types.CallbackQuery):
    logging.info(f"User '{get_user_display(callback_query.from_user)}' выбрал обмен THB.")
    await callback_query.message.edit_text(
        "THB\nВыберите направление обмена:",
        reply_markup=get_thb_directions_keyboard()
    )

@router.callback_query(lambda c: c.data == "exchange_usdt")
async def exchange_usdt(callback_query: types.CallbackQuery):
    logging.info(f"User '{get_user_display(callback_query.from_user)}' выбрал обмен USDT.")
    await callback_query.message.edit_text(
        "USDT TRC20\nВыберите направление обмена:",
        reply_markup=get_usdt_directions_keyboard()
    )