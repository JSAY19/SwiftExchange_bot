from aiogram import Router, types, F
from aiogram.filters import Command
from src.bot.keyboards.reply_keyboards import get_main_keyboard
from src.bot.keyboards.inline_keyboards import get_exchange_main_keyboard, get_usdt_rub_directions_keyboard, get_exchange_type_keyboard, get_usdt_to_thb_keyboard, get_thb_to_usdt_keyboard, get_exchange_type_keyboard_rub_to_thb, get_rub_to_thb_keyboard, get_thb_to_rub_keyboard
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

"""-----------------------------------------------------------------------------------------------
--------------------------------------------------------------------------------------------------"""

@router.callback_query(F.data == "exchange_usdt_or_rub")
async def exchange_usdt(callback_query: types.CallbackQuery):
    try:
        logging.info(f"User '{get_user_display(callback_query.from_user)}' выбрал обмен USDT or RUB.")
        await callback_query.message.edit_text(
            "THB\nВыберите направление обмена:",
            reply_markup=get_usdt_rub_directions_keyboard()
        )
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Ошибка в exchange_usdt_or_rub: {str(e)}")
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
            "🌐 <b>В банкомате</b>\n"
            "Мин. сумма: 🎉✨✨\n"
            "Макс. сумма: 🎉✨✨\n\n"
            "🏢 <b>В отеле</b>\n"
            "Мин. сумма: 🎉✨✨\n"
            "Макс. сумма: 🎉✨✨",
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


@router.callback_query(F.data.in_(["exchange_in_ATM", "exchange_in_hotel"]))
async def show_atm_or_hotel(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "exchange_in_ATM":
        receive_type = "Получение в банкомате"
    else:
        receive_type = "Получение в отеле"
    # Сохраняем выбор в состояние
    await state.update_data(receive_type=receive_type)

    text = (
        "<b>Обмен</b>\n\n"
        "Заявка №...\n"
        f"{receive_type}\n"
        "Тип обмена: USDT -> THB\n"
        "Курс: 🎈🎈🎈 USDT -> 🎈🎈🎈 THB\n"
        "Сеть: TRC20\n"
        "Мин. сумма: 🎈🎈🎈\n"
        "Макс. сумма: 🎈🎈🎈\n\n"
        "Введите сумму USDT, которую вы хотите обменять:"
    )
    await callback_query.message.edit_text(
        text,
        reply_markup=get_usdt_to_thb_keyboard(),
        parse_mode="HTML"
    )
    await callback_query.answer()


@router.callback_query(F.data.in_(["enter_thb_amount", "enter_usdt_amount"]))
async def show_amount(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    receive_type = data.get("receive_type", "")

    if callback_query.data == "enter_thb_amount":
        currency_text = "Введите сумму THB (Баты), которую вы хотите получить:"
        reply_markup = get_thb_to_usdt_keyboard()
    else:
        currency_text = "Введите сумму USDT, которую вы хотите обменять:"
        reply_markup = get_usdt_to_thb_keyboard()

    text = (
        "<b>Обмен</b>\n\n"
        "Заявка №...\n"
        f"{receive_type}\n"
        "Тип обмена: USDT -> THB\n"
        "Курс: 🎈🎈🎈 USDT -> 🎈🎈🎈 THB\n"
        "Сеть: TRC20\n"
        "Мин. сумма: 🎈🎈🎈\n"
        "Макс. сумма: 🎈🎈🎈\n\n"
        f"{currency_text}"
    )
    await callback_query.message.edit_text(
        text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    await callback_query.answer()

"""-----------------------------------------------------------------------------------------------
--------------------------------------------------------------------------------------------------"""

@router.callback_query(F.data == "rub_to_thb")
async def rub_to_thb(callback_query: types.CallbackQuery):
    try:
        logging.info(f"User '{get_user_display(callback_query.from_user)}' выбрал RUB → THB.")
        await callback_query.message.edit_text(
            "<b>Выбор обмена</b>\n\n"
            "<b>Варианты обмена:</b>\n\n"
            "🌐 <b>В банкомате</b>\n"
            "Мин. сумма: 🎉✨✨\n"
            "Макс. сумма: 🎉✨✨\n\n"
            "🏢 <b>В отеле</b>\n"
            "Мин. сумма: 🎉✨✨\n"
            "Макс. сумма: 🎉✨✨",
            reply_markup=get_exchange_type_keyboard_rub_to_thb(),
            parse_mode="HTML"
        )
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Ошибка в usdt_to_thb: {str(e)}")
        try:
            await callback_query.answer("Произошла ошибка. Попробуйте снова.")
        except:
            logging.error("Не удалось отправить ответ на callback_query")

@router.callback_query(F.data.in_(["exchange_in_ATM_rub", "exchange_in_hotel_rub"]))
async def show_atm_or_hotel(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "exchange_in_ATM_rub":
        receive_type_rub = "Получение в банкомате"
    else:
        receive_type_rub = "Получение в отеле"
    # Сохраняем выбор в состояние
    await state.update_data(receive_type=receive_type_rub)

    text = (
        "<b>Обмен</b>\n\n"
        "Заявка №...\n"
        f"{receive_type_rub}\n"
        "Тип обмена: RUB -> THB\n"
        "Курс: 🎈🎈🎈 RUB -> 🎈🎈🎈 THB\n"
        "Мин. сумма: 🎈🎈🎈\n"
        "Макс. сумма: 🎈🎈🎈\n\n"
        "Введите сумму RUB, которую хотите обменять:"
    )
    await callback_query.message.edit_text(
        text,
        reply_markup=get_rub_to_thb_keyboard(),
        parse_mode="HTML"
    )
    await callback_query.answer()

@router.callback_query(F.data.in_(["enter_thb_amount_rub", "enter_rub_amount"]))
async def show_amount(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    receive_type = data.get("receive_type", "")

    if callback_query.data == "enter_thb_amount_rub":
        currency_text = "Введите сумму THB (Баты), которую вы хотите получить:"
        reply_markup = get_thb_to_rub_keyboard()
    else:
        currency_text = "Введите сумму RUB, которую вы хотите обменять:"
        reply_markup = get_rub_to_thb_keyboard()

    text = (
        "<b>Обмен</b>\n\n"
        "Заявка №...\n"
        f"{receive_type}\n"
        "Тип обмена: RUB -> THB\n"
        "Курс: 🎈🎈🎈 RUB -> 🎈🎈🎈 THB\n"
        "Мин. сумма: 🎈🎈🎈\n"
        "Макс. сумма: 🎈🎈🎈\n\n"
        f"{currency_text}"
    )
    await callback_query.message.edit_text(
        text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    await callback_query.answer()