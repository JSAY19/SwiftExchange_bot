# -------------------- Импорты и константы --------------------
from aiogram import Router, types, F
from aiogram.filters import Command
from src.bot.keyboards.reply_keyboards import get_main_keyboard
import src.bot.keyboards.inline_keyboards as inline_keyboards
from datetime import datetime, timedelta
import asyncio
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
import logging
from .colors_logs import *
from .colors_logs import get_user_display

USDT_TO_THB_RATE = 35
RUB_TO_THB_RATE = 2.5

router = Router()

# -------------------- Главные команды --------------------

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
            reply_markup=inline_keyboards.get_exchange_main_keyboard()
        )
    except Exception as e:
        logging.error(f"Ошибка в exchange_main: {str(e)}")
        await message.answer("Извините, произошла ошибка. Попробуйте позже или обратитесь в поддержку.")

@router.callback_query(F.data == "exchange_main")
async def exchange_main_back(callback_query: types.CallbackQuery):
    await safe_edit_text(
        callback_query.message,
        "Выберите валюту, которую вы желаете получить:",
        reply_markup=inline_keyboards.get_exchange_main_keyboard()
    )
    await callback_query.answer()

@router.message(F.text == "👩‍💻 Профиль")
async def get_profile_main(message: types.Message):
    try:
        logging.info(f"User '{get_user_display(message.from_user)}' выбрал 'Профиль'.")
        await message.answer(
            f"💢Ваш профиль💢\n\n💫Ваш id: {message.from_user.id}\n 💫Количество успешных обменов: 🎈🎈 \n",
            reply_markup=inline_keyboards.get_profile_main_user_keyboard()
        )
    except Exception as e:
        logging.error(f"Ошибка в get_profile_main: {str(e)}")
        try:
            await message.answer("Произошла ошибка. Попробуйте снова.")
        except:
            logging.error("Не удалось отправить ответ на message")

@router.message(F.text == "✨ Отзывы")
async def go_to_reviews(message: types.Message):
    await message.answer(
        "💬 Оставить или прочитать отзывы о нашем обменнике вы можете в нашем чате: \n\n"
        "👉 <a href='https://t.me/+w1iU4eQUG_oyYTIy'>Отзывы | Xchanger</a>",
        parse_mode="HTML"
    )

# -------------------- Сценарий обмена --------------------

## --- 1. Выбор направления ---

@router.callback_query(F.data == "exchange_usdt_or_rub")
async def exchange_usdt(callback_query: types.CallbackQuery):
    try:
        logging.info(f"User '{get_user_display(callback_query.from_user)}' выбрал обмен USDT or RUB.")
        await safe_edit_text(
            callback_query.message,
            "📌THB\nВыберите направление обмена:",
            reply_markup=inline_keyboards.get_usdt_rub_directions_keyboard()
        )
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Ошибка в exchange_usdt_or_rub: {str(e)}")
        await callback_query.answer("Произошла ошибка. Попробуйте снова.")

@router.callback_query(F.data == "usdt_to_thb")
async def usdt_to_thb(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        logging.info(f"User '{get_user_display(callback_query.from_user)}' выбрал USDT → THB.")
        await state.update_data(exchange_type="USDT->THB")
        await safe_edit_text(
            callback_query.message,
            "<b>🎈Выбор обмена🎈</b>\n\n"
            "<b>⚙ Варианты обмена:</b>\n\n"
            "🌐 <b>В банкомате</b>\n"
            "Мин. сумма: 10000 THB (баты), если ниже - комиссия 300 THB (баты)\n"
            "Макс. сумма: ∞\n\n"
            "🏢 <b>В отеле</b>\n"
            "Мин. сумма: 10000 THB (баты), если ниже - комиссия 300 THB (баты)\n"
            "Макс. сумма: ∞",
            reply_markup=inline_keyboards.get_exchange_type_keyboard(),
            parse_mode="HTML"
        )
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Ошибка в usdt_to_thb: {str(e)}")
        try:
            await callback_query.answer("Произошла ошибка. Попробуйте снова.")
        except:
            logging.error("Не удалось отправить ответ на callback_query")

@router.callback_query(F.data == "rub_to_thb")
async def rub_to_thb(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        logging.info(f"User '{get_user_display(callback_query.from_user)}' выбрал RUB → THB.")
        await state.update_data(exchange_type="RUB->THB")
        await safe_edit_text(
            callback_query.message,
            "<b>🎈Выбор обмена🎈</b>\n\n"
            "<b>⚙ Варианты обмена:</b>\n\n"
            "🌐 <b>В банкомате</b>\n"
            "Мин. сумма: 10000 THB (баты), если ниже - комиссия 300 THB (баты)\n"
            "Макс. сумма: ∞\n\n"
            "🏢 <b>В отеле</b>\n"
            "Мин. сумма: 10000 THB (баты), если ниже - комиссия 300 THB (баты)\n"
            "Макс. сумма: ∞",
            reply_markup=inline_keyboards.get_exchange_type_keyboard_rub_to_thb(),
            parse_mode="HTML"
        )
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Ошибка в rub_to_thb: {str(e)}")
        try:
            await callback_query.answer("Произошла ошибка. Попробуйте снова.")
        except:
            logging.error("Не удалось отправить ответ на callback_query")

## --- 2. USDT → THB ---

@router.callback_query(F.data.in_(["exchange_in_ATM", "exchange_in_hotel"]))
async def show_atm_or_hotel(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "exchange_in_ATM":
        receive_type = "Получение в банкомате"
    else:
        receive_type = "Получение в отеле"
    await state.update_data(receive_type=receive_type, input_type="input_usdt")
    text = (
        "<b>Обмен</b>\n\n"
        "Заявка №...\n"
        f"{receive_type}\n"
        f"Курс: <b>1 USDT = {USDT_TO_THB_RATE} THB</b>\n"
        "Сеть: TRC20\n"
        "Мин. сумма: 10000 THB (баты), если ниже - комиссия 300 THB (баты)\n"
        "Макс. сумма: ∞\n\n"
        "Введите сумму USDT, которую вы хотите обменять:"
    )
    await safe_edit_text(
        callback_query.message,
        text,
        reply_markup=inline_keyboards.get_usdt_to_thb_keyboard(),
        parse_mode="HTML"
    )
    await callback_query.answer()

@router.callback_query(F.data.in_(["enter_thb_amount", "enter_usdt_amount"]))
async def switch_currency_usdt(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    receive_type = data.get("receive_type", "")
    exchange_type = data.get("exchange_type", "USDT->THB")
    if callback_query.data == "enter_thb_amount":
        await state.update_data(input_type="input_thb")
        text = (
            "<b>Обмен</b>\n\n"
            "Заявка №...\n"
            f"{receive_type}\n"
            f"Курс: <b>1 USDT = {USDT_TO_THB_RATE} THB</b>\n"
            "Сеть: TRC20\n"
            "Мин. сумма: 10000 THB (баты), если ниже - комиссия 300 THB (баты)\n"
            "Макс. сумма: ∞\n\n"
            "Введите сумму THB, которую вы хотите получить:"
        )
        reply_markup = inline_keyboards.get_thb_to_usdt_keyboard()
    else:
        await state.update_data(input_type="input_usdt")
        text = (
            "<b>Обмен</b>\n\n"
            "Заявка №...\n"
            f"{receive_type}\n"
            f"Курс: <b>1 USDT = {USDT_TO_THB_RATE} THB</b>\n"
            "Сеть: TRC20\n"
            "Мин. сумма: 10000 THB (баты), если ниже - комиссия 300 THB (баты)\n"
            "Макс. сумма: ∞\n\n"
            "Введите сумму USDT, которую вы хотите обменять:"
        )
        reply_markup = inline_keyboards.get_usdt_to_thb_keyboard()
    await safe_edit_text(
        callback_query.message,
        text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    await callback_query.answer()

## --- 3. RUB → THB ---

@router.callback_query(F.data.in_(["exchange_in_ATM_rub", "exchange_in_hotel_rub"]))
async def show_atm_or_hotel_rub(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "exchange_in_ATM_rub":
        receive_type = "Получение в банкомате"
    else:
        receive_type = "Получение в отеле"
    await state.update_data(receive_type=receive_type, input_type="input_rub")
    text = (
        "<b>Обмен</b>\n\n"
        "Заявка №...\n"
        f"{receive_type}\n"
        f"Курс: <b>1 RUB = {1/RUB_TO_THB_RATE:.4f} THB</b>\n"
        "Мин. сумма: 10000 THB (баты), если ниже - комиссия 300 THB (баты)\n"
        "Макс. сумма: ∞\n\n"
        "Введите сумму RUB, которую хотите обменять:"
    )
    await safe_edit_text(
        callback_query.message,
        text,
        reply_markup=inline_keyboards.get_rub_to_thb_keyboard(),
        parse_mode="HTML"
    )
    await callback_query.answer()

@router.callback_query(F.data.in_(["enter_thb_amount_rub", "enter_rub_amount"]))
async def switch_currency_rub(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    receive_type = data.get("receive_type", "")
    exchange_type = data.get("exchange_type", "RUB->THB")
    if callback_query.data == "enter_thb_amount_rub":
        await state.update_data(input_type="input_thb")
        text = (
            "<b>Обмен</b>\n\n"
            "Заявка №...\n"
            f"{receive_type}\n"
            f"Курс: <b>1 RUB = {1/RUB_TO_THB_RATE:.4f} THB</b>\n"
            "Мин. сумма: 10000 THB (баты), если ниже - комиссия 300 THB (баты)\n"
            "Макс. сумма: ∞\n\n"
            "Введите сумму THB, которую вы хотите получить:"
        )
        reply_markup = inline_keyboards.get_thb_to_rub_keyboard()
    else:
        await state.update_data(input_type="input_rub")
        text = (
            "<b>Обмен</b>\n\n"
            "Заявка №...\n"
            f"{receive_type}\n"
            f"Курс: <b>1 RUB = {1/RUB_TO_THB_RATE:.4f} THB</b>\n"
            "Мин. сумма: 10000 THB (баты), если ниже - комиссия 300 THB (баты)\n"
            "Макс. сумма: ∞\n\n"
            "Введите сумму RUB, которую хотите обменять:"
        )
        reply_markup = inline_keyboards.get_rub_to_thb_keyboard()
    await safe_edit_text(
        callback_query.message,
        text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    await callback_query.answer()

# --- Ввод суммы и подтверждение/отмена для всех сценариев ---

@router.message(F.text.regexp(r'^\d+(\.\d+)?$'))
async def handle_amount_input(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        data = await state.get_data()
        receive_type = data.get("receive_type", "")
        exchange_type = data.get("exchange_type", "USDT->THB")
        input_type = data.get("input_type", "input_usdt")
        commission_text = ""
        commission = 0
        in_currency = "USDT"
        out_currency = "THB"
        rate = USDT_TO_THB_RATE if exchange_type == "USDT->THB" else RUB_TO_THB_RATE
        amount_in = 0
        amount_out = 0

        if exchange_type == "USDT->THB":
            if input_type == "input_thb":
                amount_thb = amount
                amount_usdt = amount_thb / USDT_TO_THB_RATE
                if amount_thb < 10000:
                    commission = 300 / USDT_TO_THB_RATE
                    amount_usdt += commission
                    commission_text = f"\nВключена комиссия 300 THB ({commission:.2f} USDT)"
                amount_in = amount_usdt
                amount_out = amount_thb
            else:
                amount_usdt = amount
                amount_thb = amount_usdt * USDT_TO_THB_RATE
                if amount_thb < 10000:
                    commission = 300 / USDT_TO_THB_RATE
                    amount_usdt += commission
                    commission_text = f"\nВключена комиссия 300 THB ({commission:.2f} USDT)"
                amount_in = amount_usdt
                amount_out = amount_thb
        elif exchange_type == "RUB->THB":
            in_currency = "RUB"
            if input_type == "input_thb":
                amount_thb = amount
                amount_rub = amount_thb * RUB_TO_THB_RATE
                if amount_thb < 10000:
                    commission = 300 * RUB_TO_THB_RATE
                    amount_rub += commission
                    commission_text = f"\nВключена комиссия 300 THB ({commission:.2f} RUB)"
                amount_in = amount_rub
                amount_out = amount_thb
            else:
                amount_rub = amount
                amount_thb = amount_rub / RUB_TO_THB_RATE
                if amount_thb < 10000:
                    commission = 300 * RUB_TO_THB_RATE
                    amount_rub += commission
                    commission_text = f"\nВключена комиссия 300 THB ({commission:.2f} RUB)"
                amount_in = amount_rub
                amount_out = amount_thb

        await state.update_data(
            amount_in=amount_in,
            amount_out=amount_out,
            commission=commission,
            commission_text=commission_text,
            in_currency=in_currency,
            out_currency=out_currency,
            rate=rate
        )

        text = (
            f"<b>Обмен</b>\n\n"
            f"Заявка №...\n"
            f"{receive_type}\n"
            f"Курс: <b>1 {in_currency} = {rate} {out_currency}</b>\n"
            f"Вы отдаёте: {amount_in:.2f} {in_currency}{commission_text}\n"
            f"Получаете: {amount_out:.2f} {out_currency}\n\n"
            f"Подтвердите обмен:"
        )
        await message.answer(
            text,
            reply_markup=inline_keyboards.get_confirm_exchange_keyboard(),
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer(
            "Пожалуйста, введите корректную сумму.",
            reply_markup=inline_keyboards.get_usdt_to_thb_keyboard()
        )

@router.callback_query(F.data == "confirm_exchange")
async def confirm_exchange(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        user = callback_query.from_user
        tg_id = user.id
        username = user.username or "-"
        exchange_type = data.get("exchange_type", "")
        receive_type = data.get("receive_type", "")
        amount_in = data.get("amount_in")
        amount_out = data.get("amount_out")
        commission_text = data.get("commission_text", "")
        in_currency = data.get("in_currency", "")
        out_currency = data.get("out_currency", "")
        rate = data.get("rate", "")
        text = (
            f"Новая заявка!\n"
            f"Пользователь: @{username} (tg_id: {tg_id})\n"
            f"Тип обмена: {exchange_type}\n"
            f"{receive_type}\n"
            f"Курс: 1 {in_currency} = {rate} {out_currency}\n"
            f"Отдаёт: {amount_in:.2f} {in_currency}{commission_text}\n"
            f"Получает: {amount_out:.2f} {out_currency}\n"
        )
        await callback_query.bot.send_message(6659909595, text)
        await safe_edit_text(
            callback_query.message,
            "✅ Заявка на рассмотрении! Ожидайте дальнейших инструкций.",
            reply_markup=inline_keyboards.get_exchange_main_keyboard()
        )
    except Exception as e:
        logging.error(f"Ошибка при подтверждении обмена: {str(e)}")
        await callback_query.answer("Произошла ошибка. Попробуйте снова.")

@router.callback_query(F.data == "cancel_exchange")
async def cancel_exchange(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        await safe_edit_text(callback_query.message,
            "❌ Обмен отменен.",
            reply_markup=inline_keyboards.get_exchange_main_keyboard()
        )
    except Exception as e:
        logging.error(f"Ошибка при отмене обмена: {str(e)}")
        await callback_query.answer("Произошла ошибка. Попробуйте снова.")

@router.callback_query(F.data == "confirm_exchange_rub")
async def confirm_exchange_rub(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        user = callback_query.from_user
        tg_id = user.id
        username = user.username or "-"
        exchange_type = data.get("exchange_type", "")
        receive_type = data.get("receive_type", "")
        amount_in = data.get("amount_in")
        amount_out = data.get("amount_out")
        commission_text = data.get("commission_text", "")
        in_currency = data.get("in_currency", "")
        out_currency = data.get("out_currency", "")
        rate = data.get("rate", "")
        text = (
            f"Новая заявка!\n"
            f"Пользователь: @{username} (tg_id: {tg_id})\n"
            f"Тип обмена: {exchange_type}\n"
            f"{receive_type}\n"
            f"Курс: 1 {in_currency} = {rate} {out_currency}\n"
            f"Отдаёт: {amount_in:.2f} {in_currency}{commission_text}\n"
            f"Получает: {amount_out:.2f} {out_currency}\n"
        )
        await callback_query.bot.send_message(6659909595, text)
        await safe_edit_text(
            callback_query.message,
            "✅ Заявка на рассмотрении! Ожидайте дальнейших инструкций.",
            reply_markup=inline_keyboards.get_exchange_main_keyboard()
        )
    except Exception as e:
        logging.error(f"Ошибка при подтверждении обмена: {str(e)}")
        await callback_query.answer("Произошла ошибка. Попробуйте снова.")

@router.callback_query(F.data == "cancel_exchange_rub")
async def cancel_exchange_rub(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        await safe_edit_text(callback_query.message,
            "❌ Обмен отменен.",
            "<b>Выберите валюту, которую хотите получить</b>\n\n",
            reply_markup=inline_keyboards.get_exchange_main_keyboard()
        )
    except Exception as e:
        logging.error(f"Ошибка при отмене обмена: {str(e)}")
        await callback_query.answer("Произошла ошибка. Попробуйте снова.")

# -------------------- Общие обработчики --------------------

async def safe_edit_text(message, *args, **kwargs):
    try:
        await message.edit_text(*args, **kwargs)
    except Exception as e:
        if "message is not modified" in str(e):
            pass  # Игнорируем эту ошибку
        else:
            logging.error(f"Ошибка при edit_text: {str(e)}")
            # Можно отправить ответ пользователю, если нужно

    