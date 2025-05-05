from aiogram import Router, types, F
from aiogram.filters import Command
from src.bot.keyboards.reply_keyboards import get_main_keyboard
from datetime import datetime, timedelta
import asyncio
router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Добро пожаловать в SwiftExchange Bot!\n"
        "Выберите действие из меню ниже:",
        reply_markup=get_main_keyboard()
    ) 
