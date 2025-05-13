# -------------------- Импорты и константы --------------------
from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from src.bot.keyboards.reply_keyboards import get_main_keyboard
import src.bot.keyboards.inline_keyboards as inline_keyboards
from datetime import datetime, timedelta
import asyncio
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
import logging
from .colors_logs import *
from .colors_logs import get_user_display
import uuid
import os
import json

USDT_TO_THB_RATE = 35
RUB_TO_THB_RATE = 2.5

router = Router()

# Глобальная переменная для хранения текущего номера заявки
CURRENT_REQUEST_ID = 1

def get_next_request_id():
    global CURRENT_REQUEST_ID
    CURRENT_REQUEST_ID += 1
    return CURRENT_REQUEST_ID

# Путь к файлу с историей обменов
EXCHANGE_HISTORY_FILE = "exchange_history.json"

def load_exchange_history():
    if os.path.exists(EXCHANGE_HISTORY_FILE):
        with open(EXCHANGE_HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_exchange_history(history):
    with open(EXCHANGE_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def add_exchange_to_history(user_id: int, exchange_data: dict):
    history = load_exchange_history()
    if str(user_id) not in history:
        history[str(user_id)] = []
    
    # Добавляем дату и время обмена
    exchange_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history[str(user_id)].append(exchange_data)
    save_exchange_history(history)

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
            "💨 Выберите валюту, которую вы желаете получить:",
            reply_markup=inline_keyboards.get_exchange_main_keyboard()
        )
    except Exception as e:
        logging.error(f"Ошибка в exchange_main: {str(e)}")
        await message.answer("Извините, произошла ошибка. Попробуйте позже или обратитесь в поддержку.")

@router.callback_query(F.data == "exchange_main")
async def exchange_main_back(callback_query: types.CallbackQuery):
    await safe_edit_text(
        callback_query.message,
        "💨 Выберите валюту, которую вы желаете получить:",
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
            "<b>💱 Выбор обмена 💱</b>\n\n"
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
        "💱 <b>Обмен</b>\n\n"
        "💌 Заявка №...\n"
        f"💨 {receive_type}\n"
        f"💱 Курс: <b>1 USDT = {USDT_TO_THB_RATE} THB</b>\n"
        "✔ Сеть: TRC20\n"
        "💰 Мин. сумма: 10000 THB (баты), если ниже - комиссия 300 THB (баты)\n"
        "💰 Макс. сумма: ∞\n\n"
        "<b>❕ Введите сумму USDT, которую вы хотите обменять:</b>"
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
            "💱 <b>Обмен</b>\n\n"
            "💌 Заявка №...\n"
            f"💨 {receive_type}\n"
            f"💱 Курс: <b>1 USDT = {USDT_TO_THB_RATE} THB</b>\n"
            "✔ Сеть: TRC20\n"
            "💰 Мин. сумма: 10000 THB (баты), если ниже - комиссия 300 THB (баты)\n"
            "💰 Макс. сумма: ∞\n\n"
            "<b>❕ Введите сумму THB, которую вы хотите получить:</b>"
        )
        reply_markup = inline_keyboards.get_thb_to_usdt_keyboard()
    else:
        await state.update_data(input_type="input_usdt")
        text = (
            "💱 <b>Обмен</b>\n\n"
            "💌 Заявка №...\n"
            f"💨 {receive_type}\n"
            f"💱 Курс: <b>1 USDT = {USDT_TO_THB_RATE} THB</b>\n"
            "✔ Сеть: TRC20\n"
            "Мин. сумма: 10000 THB (баты), если ниже - комиссия 300 THB (баты)\n"
            "💰 Макс. сумма: ∞\n\n"
            "<b>❕ Введите сумму USDT, которую вы хотите обменять:</b>"
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
        "💱 <b>Обмен</b>\n\n"
        "💌 Заявка №...\n"
        f"💨 {receive_type}\n"
        f"💱 Курс: <b>1 RUB = {1/RUB_TO_THB_RATE:.4f} THB</b>\n"
        "💰 Мин. сумма: 10000 THB (баты), если ниже - комиссия 300 THB (баты)\n"
        "💰 Макс. сумма: ∞\n\n"
        "<b>❕ Введите сумму RUB, которую хотите обменять:</b>"
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
            "💱 <b>Обмен</b>\n\n"
            "💌 Заявка №...\n"
            f"💨 {receive_type}\n"
            f"💱 Курс: <b>1 RUB = {1/RUB_TO_THB_RATE:.4f} THB</b>\n"
            "💰 Мин. сумма: 10000 THB (баты), если ниже - комиссия 300 THB (баты)\n"
            "💰 Макс. сумма: ∞\n\n"
            "<b>❕ Введите сумму THB, которую вы хотите получить:</b>"
        )
        reply_markup = inline_keyboards.get_thb_to_rub_keyboard()
    else:
        await state.update_data(input_type="input_rub")
        text = (
            "💱 <b>Обмен</b>\n\n"
            "💌 Заявка №...\n"
            f"💨 {receive_type}\n"
            f"💱 Курс: <b>1 RUB = {1/RUB_TO_THB_RATE:.4f} THB</b>\n"
            "💰 Мин. сумма: 10000 THB (баты), если ниже - комиссия 300 THB (баты)\n"
            "💰 Макс. сумма: ∞\n\n"
            "<b>❕ Введите сумму RUB, которую хотите обменять:</b>"
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
            f"💱 <b>Обмен</b>\n\n"
            f"💌 Заявка №...\n"
            f"💨 {receive_type}\n"
            f"💱 Курс: <b>1 {in_currency} = {rate} {out_currency}</b>\n"
            f"💸 Вы отдаёте: {amount_in:.2f} {in_currency}{commission_text}\n"
            f"💰 Получаете: {amount_out:.2f} {out_currency}\n\n"
            f"❕<b>Подтвердите заявку на обмен:</b>"
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
        exchange_type = data.get("exchange_type", "")
        in_currency = data.get("in_currency", "")
        
        if exchange_type == "USDT->THB":
            payment_details = (
                "💳 <b>Реквизиты для оплаты:</b>\n\n"
                f"💸 Сумма к оплате: {data['amount_in']:.2f} USDT\n"
                f"💰 Вы получите: {data['amount_out']:.2f} THB\n\n"
                "📝 <b>USDT (TRC20)</b>\n"
                "Кошелек: <code>TMjRsz5SZ16adPMf11QQNZDHYkwQ58nSDd</code>\n"
                "Сеть: TRC20\n\n"
                "⚠️ После оплаты, пожалуйста, отправьте скриншот подтверждения перевода."
            )
        else:  # RUB->THB
            payment_details = (
                "💳 <b>Реквизиты для оплаты:</b>\n\n"
                f"💸 Сумма к оплате: {data['amount_in']:.2f} RUB\n"
                f"💰 Вы получите: {data['amount_out']:.2f} THB\n\n"
                "📝 <b>Рублевый перевод</b>\n"
                "Номер: <code>+79263691059</code>\n"
                "Банки: Сбербанк, Альфа, Тинькофф\n"
                "Получатель: Виталий Водолазов\n\n"
                "⚠️ После оплаты, пожалуйста, отправьте скриншот подтверждения перевода."
            )
        
        await safe_edit_text(
            callback_query.message,
            payment_details,
            reply_markup=inline_keyboards.get_cancel_exchange_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state("waiting_for_payment_screenshot")
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Ошибка при запросе оплаты: {str(e)}")
        await callback_query.answer("Произошла ошибка. Попробуйте снова.")

@router.message(F.photo, StateFilter("waiting_for_payment_screenshot"))
async def handle_payment_screenshot(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        user = message.from_user
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
        
        request_id = get_next_request_id()
        await state.update_data(request_id=request_id)

        # Отправляем заявку менеджеру
        text = (
            f"💌 Новая заявка #{request_id}!\n\n"
            f"💨 Пользователь: @{username} (tg_id: {tg_id})\n"
            f"💱 Тип обмена: {exchange_type}\n"
            f"💨 {receive_type}\n"
            f"💱 Курс: 1 {in_currency} = {rate} {out_currency}\n"
            f"💸 Отдал: {amount_in:.2f} {in_currency}{commission_text}\n"
            f"💰 К получению: {amount_out:.2f} {out_currency}\n"
        )
        
        # Отправляем скриншот менеджеру
        await message.bot.send_photo(6659909595, message.photo[-1].file_id)
        # Отправляем сообщение менеджеру с кнопками
        await message.bot.send_message(6659909595, text, reply_markup=inline_keyboards.get_manager_action_keyboard(request_id))
        
        # Отправляем подтверждение пользователю
        await message.answer(
            "✅ Заявка на обмен отправлена менеджеру! Ожидайте дальнейших инструкций.\n\n Если возникнут какие-либо вопросы, с вами может связаться менеджер.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
    except Exception as e:
        logging.error(f"Ошибка при обработке скриншота оплаты: {str(e)}")
        await message.answer("Произошла ошибка. Попробуйте снова.")

@router.callback_query(F.data.startswith("manager_confirm_"))
async def handle_manager_confirm(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        request_id = callback_query.data.split("_")[-1]
        # Получаем данные о заявке из сообщения
        message_text = callback_query.message.text
        username = message_text.split("@")[1].split(" ")[0]
        user_id = int(message_text.split("tg_id: ")[1].split(")")[0])
        
        # Отправляем уведомление менеджеру
        await callback_query.message.edit_text(
            f"{callback_query.message.text}\n\n✅ Заявка подтверждена менеджером",
            reply_markup=None
        )
        
        # Отправляем уведомление пользователю
        await callback_query.bot.send_message(
            user_id,
            f"✅ Ваша заявка #{request_id} подтверждена менеджером!"
        )
        
        # Определяем тип получения и отправляем соответствующие инструкции
        if "Получение в отеле" in message_text:
            await callback_query.bot.send_message(
                user_id,
                "🏨 <b>Инструкция по получению в отеле:</b>\n\n"
                "1. Придите по адресу: <a href='https://maps.app.goo.gl/YUBKHTMEw29DJby18'>Отель</a>\n"
                "2. Покажите на рецепшене скриншот подтверждения перевода\n"
                "3. Получите ваши средства",
                parse_mode="HTML"
            )
        else:  # Получение в банкомате
            # Отправляем видео-инструкции
            video_dir = "Video"
            for video_file in os.listdir(video_dir):
                if video_file.endswith(('.mp4', '.avi', '.mov')):
                    video_path = os.path.join(video_dir, video_file)
                    await callback_query.bot.send_video(
                        user_id,
                        FSInputFile(video_path)
                    )
            
            # Отправляем скриншоты
            for i in range(1, 3):
                image_path = f"pictures/{i}.jpg"
                if os.path.exists(image_path):
                    await callback_query.bot.send_photo(
                        user_id,
                        FSInputFile(image_path)
                    )
        
        # Отправляем запрос подтверждения получения
        await callback_query.bot.send_message(
            user_id,
            "Пожалуйста, подтвердите получение средств:",
            reply_markup=inline_keyboards.get_receipt_confirmation_keyboard()
        )
        
    except Exception as e:
        logging.error(f"Ошибка при подтверждении заявки менеджером: {str(e)}")
        await callback_query.answer("Произошла ошибка. Попробуйте снова.")

@router.callback_query(F.data.startswith("manager_reject_"))
async def handle_manager_reject(callback_query: types.CallbackQuery):
    try:
        # Получаем username пользователя из сообщения
        message_text = callback_query.message.text
        username = message_text.split("@")[1].split(" ")[0]
        
        # Отправляем уведомление менеджеру
        await callback_query.message.edit_text(
            f"{callback_query.message.text}\n\n❌ Заявка отклонена менеджером",
            reply_markup=None
        )
        
        # Отправляем сообщение менеджеру о необходимости связаться с пользователем
        await callback_query.bot.send_message(
            6659909595,
            f"⚠️ Свяжитесь с @{username} для уточнения деталей"
        )
        
    except Exception as e:
        logging.error(f"Ошибка при отклонении заявки менеджером: {str(e)}")
        await callback_query.answer("Произошла ошибка. Попробуйте снова.")

@router.callback_query(F.data == "receipt_confirmed")
async def handle_receipt_confirmation(callback_query: types.CallbackQuery, state: FSMContext = None):
    try:
        get_next_request_id()
        # Получаем данные о заявке из сообщения и FSMContext
        message_text = callback_query.message.text
        request_id = message_text.split("#")[1].split("!")[0] if "#" in message_text else "N/A"
        # Пытаемся получить подробные данные из FSMContext
        data = None
        if state:
            try:
                data = await state.get_data()
            except Exception:
                data = None
        # Формируем запись для истории
        exchange_data = {
            "request_id": request_id,
            "status": "completed",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        if data:
            exchange_data.update({
                "exchange_type": data.get("exchange_type", "-"),
                "receive_type": data.get("receive_type", "-"),
                "amount_in": data.get("amount_in", "-"),
                "in_currency": data.get("in_currency", "-"),
                "amount_out": data.get("amount_out", "-"),
                "out_currency": data.get("out_currency", "-"),
                "rate": data.get("rate", "-"),
            })
        add_exchange_to_history(callback_query.from_user.id, exchange_data)
        await callback_query.message.edit_text(
            "✅ Спасибо за подтверждение получения! Обмен успешно завершен.",
            reply_markup=None
        )
    except Exception as e:
        logging.error(f"Ошибка при подтверждении получения: {str(e)}")
        await callback_query.answer("Произошла ошибка. Попробуйте снова.")

@router.callback_query(F.data == "support_contact")
async def handle_support_contact(callback_query: types.CallbackQuery):
    try:
        await callback_query.message.edit_text(
            "👨‍💼 Свяжитесь с поддержкой: @support_username\n\n"
            "Вы можете вернуться к подтверждению получения:",
            reply_markup=inline_keyboards.get_receipt_confirmation_keyboard()
        )
    except Exception as e:
        logging.error(f"Ошибка при запросе поддержки: {str(e)}")
        await callback_query.answer("Произошла ошибка. Попробуйте снова.")

@router.callback_query(F.data == "cancel_exchange")
async def cancel_exchange(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        await safe_edit_text(
            callback_query.message,
            "❌ Обмен отменен.\n\n 💨Выберите валюту, которую хотите получить",
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
            f"💌 Новая заявка!\n\n"
            f"💨 Пользователь: @{username} (tg_id: {tg_id})\n"
            f"💱 Тип обмена: {exchange_type}\n"
            f"💨 {receive_type}\n"
            f"💱 Курс: 1 {in_currency} = {rate} {out_currency}\n"
            f"💸 Отдаёт: {amount_in:.2f} {in_currency}{commission_text}\n"
            f"💰 Получает: {amount_out:.2f} {out_currency}\n"
        )
        # Отправляем скриншот менеджеру
        await callback_query.bot.send_photo(6659909595, callback_query.photo[-1].file_id)
        # Отправляем сообщение менеджеру
        await callback_query.bot.send_message(6659909595, text)
        await safe_edit_text(
            callback_query.message,
            "✅ Заявка на рассмотрении! Ожидайте дальнейших инструкций. \n\n Если возникнут какие-либо вопросы, с вами может связаться менеджер.",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logging.error(f"Ошибка при подтверждении обмена: {str(e)}")
        await callback_query.answer("Произошла ошибка. Попробуйте снова.")

@router.callback_query(F.data == "cancel_exchange_rub")
async def cancel_exchange_rub(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        await safe_edit_text(callback_query.message,
            "❌ Обмен отменен.",
            "<b>Выберите валюту, которую хотите получить</b>\n\n"
        )
    except Exception as e:
        logging.error(f"Ошибка при отмене обмена: {str(e)}")
        await callback_query.answer("Произошла ошибка. Попробуйте снова.")

@router.callback_query(F.data == "history_exchanges")
async def show_exchange_history(callback_query: types.CallbackQuery):
    try:
        history = load_exchange_history()
        user_id = str(callback_query.from_user.id)
        if user_id not in history or not history[user_id]:
            await callback_query.message.edit_text(
                "📜 У вас пока нет истории обменов.",
                reply_markup=inline_keyboards.get_profile_main_user_keyboard()
            )
            return
        # Формируем текст с историей обменов
        history_text = "📜 <b>История ваших обменов:</b>\n\n"
        for exchange in reversed(history[user_id][-10:]):
            # Форматируем курс
            in_cur = exchange.get('in_currency', '-')
            out_cur = exchange.get('out_currency', '-')
            rate = exchange.get('rate', '-')
            if in_cur != '-' and out_cur != '-' and rate != '-':
                rate_str = f"1 {in_cur} → {rate} {out_cur}"
            else:
                rate_str = rate
            history_text += (
                f"<b>Заявка #{exchange.get('request_id', '-')}</b>\n"
                f"<b>Дата:</b> {exchange.get('timestamp', '-')}\n"
                f"<b>Направление:</b> {exchange.get('exchange_type', '-')}\n"
                f"<b>Тип получения:</b> {exchange.get('receive_type', '-')}\n"
                f"<b>Отдал:</b> {exchange.get('amount_in', '-')} {in_cur}\n"
                f"<b>К получению:</b> {exchange.get('amount_out', '-')} {out_cur}\n"
                f"<b>Курс:</b> {rate_str}\n"
                f"<b>Статус:</b> Завершен\n\n"
            )
        await callback_query.message.edit_text(
            history_text,
            reply_markup=inline_keyboards.get_profile_main_user_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Ошибка при показе истории обменов: {str(e)}")
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

    