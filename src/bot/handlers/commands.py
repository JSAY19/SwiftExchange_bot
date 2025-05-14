# -------------------- Импорты и константы --------------------
from aiogram import Router, types, F
import aiohttp
import html  # Добавил импорт html для экранирования
# Предполагаем, что CoinGeckoClient находится в src.services.coingecko_client (или укажите правильный путь)
# Проверьте, что путь импорта CoinGeckoClient верный
from src.services.CoinGecko import CoinGeckoClient
from aiogram.filters import Command, StateFilter
from src.bot.keyboards.reply_keyboards import get_main_keyboard
import src.bot.keyboards.inline_keyboards as inline_keyboards
from datetime import datetime

# Импортируем функции и модели из вашего database.py
import src.database.database as db

from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
from .colors_logs import *
from .colors_logs import get_user_display
import os
import logging

# Глобальные переменные для клиента API и сессии
# Инициализируются в on_startup (см. конец файла с примером)
aiohttp_session_global: aiohttp.ClientSession | None = None
coingecko_client_global: CoinGeckoClient | None = None

EXCHANGER_FEE_PERCENTAGE = 0.03 # 3%

MIN_COMMISSION_THB = 300.0
MIN_THB_FOR_NO_COMMISSION = 10000.0

# --- ID Менеджера (лучше вынести в конфиг) ---
MANAGER_CHAT_ID = 6659909595  # Пример

router = Router()


# -------------------- Вспомогательная функция для обновления курсов --------------------
async def update_and_store_rates_in_fsm(state: FSMContext, client: CoinGeckoClient | None = None) -> dict | None:
    """
    Получает актуальные курсы с CoinGecko и сохраняет их в FSM.
    Возвращает словарь с курсами или None в случае ошибки.
    """
    current_client = client if client else coingecko_client_global

    if not current_client:
        logging.error("CoinGeckoClient не инициализирован (ни передан, ни глобальный)!")
        await state.update_data(current_usdt_thb_rate=None, current_rub_thb_rate=None)
        return None

    try:
        rates = await current_client.get_rate()
        if rates and isinstance(rates, dict) and 'USDT/THB' in rates and 'RUB/THB' in rates:
            usdt_thb_rate = rates.get('USDT/THB') * (1 - 0.1)
            rub_thb_rate = rates.get('RUB/THB')

            await state.update_data(
                current_usdt_thb_rate=usdt_thb_rate,
                current_rub_thb_rate=rub_thb_rate,
            )
            logging.info(f"Курсы обновлены и сохранены в FSM: USDT/THB={usdt_thb_rate}, RUB/THB={rub_thb_rate}")
            return {'USDT/THB': usdt_thb_rate, 'RUB/THB': rub_thb_rate}
        else:
            logging.warning(f"Не удалось получить корректные курсы от CoinGecko. Ответ: {rates}")
            await state.update_data(current_usdt_thb_rate=None, current_rub_thb_rate=None)
            return None
    except Exception as e:
        logging.error(f"Ошибка при получении или сохранении курсов: {e}")
        await state.update_data(current_usdt_thb_rate=None, current_rub_thb_rate=None)
        return None


# -------------------- Главные команды --------------------
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    try:
        logging.info(f"User {get_user_display(message.from_user)} /start.")
        tg_id = message.from_user.id
        username = message.from_user.username
        await db.set_user(tg_id=tg_id, username=username)

        output_path = "pictures/XchangerBot_bright.png"  # Убедитесь, что путь существует
        photo = FSInputFile(output_path)
        await message.answer_photo(
            photo=photo,
            caption="🏦 Мы предлагаем надёжные, оперативные и полностью автоматизированные услуги обмена российских рублей, USDT, THB.\n"
                    "💎 Приоритет №1 — качество нашего сервиса. Мы высоко ценим каждого нашего клиента и стремимся сделать процесс обмена максимально удобным и быстрым, чтобы Вы всегда возвращались к нам.\n"
                    "💬 → Техническая поддержка: @ВАШ_САППОРТ_ЮЗЕРНЕЙМ",  # ЗАМЕНИТЬ
            reply_markup=get_main_keyboard()
        )
    except FileNotFoundError:
        logging.error(f"Не найден файл изображения {output_path}")
        await message.answer("Извините, произошла ошибка при загрузке изображения. Команда уведомлена.")
    except Exception as e:
        logging.error(f"Ошибка в cmd_start: {str(e)}")
        await message.answer("Извините, произошла ошибка. Попробуйте позже или обратитесь в поддержку.")


@router.message(F.text == "💰 Совершить обмен")
async def exchange_main(message: types.Message, state: FSMContext):
    try:
        logging.info(f"User '{get_user_display(message.from_user)}' выбрал 'Совершить обмен'.")

        actual_rates = await update_and_store_rates_in_fsm(state)
        if not actual_rates:
            await message.answer(
                "Не удалось получить актуальные курсы обмена. Попробуйте позже или свяжитесь с поддержкой.")
            return

        await message.answer(
            "💨 Выберите валюту, которую вы желаете получить:",
            reply_markup=inline_keyboards.get_exchange_main_keyboard()
        )
    except Exception as e:
        logging.error(f"Ошибка в exchange_main: {str(e)}")
        await message.answer("Извините, произошла ошибка. Попробуйте позже или обратитесь в поддержку.")


@router.callback_query(F.data == "exchange_main")
async def exchange_main_back(callback_query: types.CallbackQuery, state: FSMContext):
    actual_rates = await update_and_store_rates_in_fsm(state)
    if not actual_rates:
        await callback_query.answer("Не удалось обновить курсы. Попробуйте еще раз.", show_alert=True)
        return

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
        tg_id = message.from_user.id

        user_history = await db.get_user_exchange_history(tg_id=tg_id, include_creation_status=False)
        successful_exchanges_count = sum(1 for item in user_history if item.status == db.Status.successful)

        await message.answer(
            f"💢Ваш профиль💢\n\n"
            f"💫Ваш id: {tg_id}\n"
            f"💫Количество успешных обменов: {successful_exchanges_count} 🎈🎈\n",
            reply_markup=inline_keyboards.get_profile_main_user_keyboard()
        )
    except Exception as e:
        logging.error(f"Ошибка в get_profile_main: {str(e)}")
        await message.answer("Произошла ошибка при загрузке профиля. Попробуйте снова.")


@router.message(F.text == "✨ Отзывы")
async def go_to_reviews(message: types.Message):
    await message.answer(
        "💬 Оставить или прочитать отзывы о нашем обменнике вы можете в нашем чате: \n\n"
        "👉 <a href='https://t.me/+w1iU4eQUG_oyYTIy'>Отзывы | Xchanger</a>",  # ЗАМЕНИТЬ
        parse_mode="HTML"
    )


# -------------------- Сценарий обмена --------------------

@router.callback_query(F.data == "exchange_usdt_or_rub")
async def exchange_usdt_or_rub_handler(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        logging.info(f"User '{get_user_display(callback_query.from_user)}' выбрал обмен USDT or RUB.")
        actual_rates = await update_and_store_rates_in_fsm(state)
        if not actual_rates:
            await callback_query.answer("Не удалось получить актуальные курсы. Попробуйте позже.", show_alert=True)
            return

        await safe_edit_text(
            callback_query.message,
            "📌THB\nВыберите направление обмена:",
            reply_markup=inline_keyboards.get_usdt_rub_directions_keyboard()
        )
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Ошибка в exchange_usdt_or_rub_handler: {str(e)}")
        await callback_query.answer("Произошла ошибка. Попробуйте снова.")


@router.callback_query(F.data == "usdt_to_thb")
async def usdt_to_thb_handler(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        logging.info(f"User '{get_user_display(callback_query.from_user)}' выбрал USDT → THB.")

        data = await state.get_data()
        current_usdt_thb = data.get('current_usdt_thb_rate')

        if current_usdt_thb is None:
            updated_rates = await update_and_store_rates_in_fsm(state)
            if not updated_rates or updated_rates.get('USDT/THB') is None:
                await callback_query.answer("Не удалось получить актуальный курс USDT/THB. Попробуйте позже.",
                                            show_alert=True)
                return
            current_usdt_thb = updated_rates.get('USDT/THB')

        await state.update_data(
            currency_from="USDT",
            currency_to="THB",
            exchange_rate_str=str(current_usdt_thb),
            request_id=None
        )

        await safe_edit_text(
            callback_query.message,
            "<b>💱 Выбор обмена (USDT → THB)</b>\n"
            f"Текущий курс для информации: <b>1 USDT ≈ {current_usdt_thb:.2f} THB</b>\n"
            "(курс для обмена будет зафиксирован на этом шаге)\n\n"
            "<b>⚙ Варианты обмена:</b>\n"
            "🌐 <b>В банкомате</b> (Мин: 10000 THB, иначе ком. 300 THB)\n"
            "🏢 <b>В отеле</b> (Мин: 10000 THB, иначе ком. 300 THB)",
            reply_markup=inline_keyboards.get_exchange_type_keyboard(),
            parse_mode="HTML"
        )
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Ошибка в usdt_to_thb_handler: {str(e)}")
        await callback_query.answer("Произошла ошибка. Попробуйте снова.")


@router.callback_query(F.data == "rub_to_thb")
async def rub_to_thb_handler(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        logging.info(f"User '{get_user_display(callback_query.from_user)}' выбрал RUB → THB.")

        data = await state.get_data()
        current_rub_thb = data.get('current_rub_thb_rate')

        if current_rub_thb is None:
            updated_rates = await update_and_store_rates_in_fsm(state)
            if not updated_rates or updated_rates.get('RUB/THB') is None:
                await callback_query.answer("Не удалось получить актуальный курс RUB/THB. Попробуйте позже.",
                                            show_alert=True)
                return
            current_rub_thb = updated_rates.get('RUB/THB')

        await state.update_data(
            currency_from="RUB",
            currency_to="THB",
            exchange_rate_str=str(current_rub_thb),
            request_id=None
        )

        await safe_edit_text(
            callback_query.message,
            "<b>🎈Выбор обмена (RUB → THB)🎈</b>\n"
            f"Текущий курс для информации: <b>1 RUB ≈ {current_rub_thb:.4f} THB</b>\n"
            "(курс для обмена будет зафиксирован на этом шаге)\n\n"
            "<b>⚙ Варианты обмена:</b>\n"
            "🌐 <b>В банкомате</b> (Мин: 10000 THB, иначе ком. 300 THB)\n"
            "🏢 <b>В отеле</b> (Мин: 10000 THB, иначе ком. 300 THB)",
            reply_markup=inline_keyboards.get_exchange_type_keyboard_rub_to_thb(),
            parse_mode="HTML"
        )
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Ошибка в rub_to_thb_handler: {str(e)}")
        await callback_query.answer("Произошла ошибка. Попробуйте снова.")


@router.callback_query(
    F.data.in_(["exchange_in_ATM", "exchange_in_hotel", "exchange_in_ATM_rub", "exchange_in_hotel_rub"]))
async def select_receive_type_handler(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        currency_from = data.get("currency_from")
        fixed_rate_for_deal_str = data.get("exchange_rate_str")

        if not currency_from or not fixed_rate_for_deal_str:
            # ... (обработка ошибки) ...
            return

        receive_type_val = ""
        input_currency_prompt_val = ""  # Изменил имя, чтобы не конфликтовать с python-ключевым словом input
        next_keyboard = None
        display_rate_text_for_deal = ""
        network_info_str = ""  # Изменил имя

        fixed_rate_for_deal_float = float(fixed_rate_for_deal_str)

        if callback_query.data in ["exchange_in_ATM", "exchange_in_hotel"]:  # USDT -> THB
            receive_type_val = "Получение в банкомате" if callback_query.data == "exchange_in_ATM" else "Получение в отеле"
            input_currency_prompt_val = "USDT, которую вы хотите обменять"
            await state.update_data(input_type="input_usdt")
            next_keyboard = inline_keyboards.get_usdt_to_thb_keyboard()
            display_rate_text_for_deal = f"1 USDT = {fixed_rate_for_deal_float:.2f} THB"
            network_info_str = "✔ Сеть: TRC20"

        elif callback_query.data in ["exchange_in_ATM_rub", "exchange_in_hotel_rub"]:  # RUB -> THB
            receive_type_val = "Получение в банкомате" if callback_query.data == "exchange_in_ATM_rub" else "Получение в отеле"
            input_currency_prompt_val = "RUB, которую вы хотите обменять"
            await state.update_data(input_type="input_rub")
            next_keyboard = inline_keyboards.get_rub_to_thb_keyboard()
            display_rate_text_for_deal = f"1 RUB = {fixed_rate_for_deal_float:.4f} THB"
            # network_info_str остается ""

        await state.update_data(receive_type=receive_type_val)

        # Формируем текст с максимальным экранированием и простым соединением
        # Экранируем все переменные перед вставкой
        safe_receive_type = html.escape(receive_type_val)
        safe_display_rate = html.escape(display_rate_text_for_deal)
        safe_network_info = html.escape(network_info_str)
        safe_input_prompt = html.escape(input_currency_prompt_val)

        text_parts = [
            "💱 <b>Обмен</b>",
            f"💨 {safe_receive_type}",
            f"💱 Курс для обмена: <b>{safe_display_rate}</b> (зафиксирован)",
        ]
        if safe_network_info:  # Добавляем, только если есть что добавлять
            text_parts.append(safe_network_info)

        text_parts.extend([
            "💰 Мин. сумма для обмена без доп. комиссии: 10000 THB",
            "(Если сумма к получению &lt; 10000 THB, будет добавлена комиссия 300 THB к сумме, которую вы отдаете)",
            f"<b>❕ Введите сумму {safe_input_prompt}:</b>"
        ])

        text = "\n\n".join(text_parts)

        logging.debug(
            f"HTML text for select_receive_type_handler (Message ID: {callback_query.message.message_id}):\n{text}")

        await safe_edit_text(
            callback_query.message,
            text,
            reply_markup=next_keyboard,
            parse_mode="HTML"
        )
        await callback_query.answer()
    except Exception as e:
        logging.exception(f"Ошибка в select_receive_type_handler для user {callback_query.from_user.id}:")
        await callback_query.answer("Произошла ошибка при выборе способа получения. Попробуйте снова.")


@router.callback_query(
    F.data.in_(["enter_thb_amount", "enter_usdt_amount", "enter_thb_amount_rub", "enter_rub_amount"]))
async def switch_input_currency_handler(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        receive_type = data.get("receive_type", "Не указан")
        currency_from = data.get("currency_from", "N/A")
        fixed_rate_for_deal_str = data.get("exchange_rate_str")

        if not fixed_rate_for_deal_str:
            await callback_query.answer("Ошибка: курс для обмена не установлен. Попробуйте начать заново.",
                                        show_alert=True)
            return

        fixed_rate_for_deal_float = float(fixed_rate_for_deal_str)
        reply_markup_val = None
        prompt_currency = ""
        display_rate_text_for_deal = ""
        network_text_val = ""  # Изменил имя

        if currency_from == "USDT":
            display_rate_text_for_deal = f"1 USDT = {fixed_rate_for_deal_float:.2f} THB"
            if callback_query.data == "enter_thb_amount":
                await state.update_data(input_type="input_thb")
                prompt_currency = "THB, которую вы хотите получить"
                reply_markup_val = inline_keyboards.get_thb_to_usdt_keyboard()
            else:
                await state.update_data(input_type="input_usdt")
                prompt_currency = "USDT, которую вы хотите обменять"
                reply_markup_val = inline_keyboards.get_usdt_to_thb_keyboard()
            network_text_val = "✔ Сеть: TRC20"

        elif currency_from == "RUB":
            display_rate_text_for_deal = f"1 RUB = {fixed_rate_for_deal_float:.4f} THB"
            if callback_query.data == "enter_thb_amount_rub":
                await state.update_data(input_type="input_thb")
                prompt_currency = "THB, которую вы хотите получить"
                reply_markup_val = inline_keyboards.get_thb_to_rub_keyboard()
            else:
                await state.update_data(input_type="input_rub")
                prompt_currency = "RUB, которую вы хотите обменять"
                reply_markup_val = inline_keyboards.get_rub_to_thb_keyboard()

        safe_receive_type = html.escape(receive_type)
        safe_display_rate = html.escape(display_rate_text_for_deal)
        safe_network_text = html.escape(network_text_val)
        safe_prompt_currency = html.escape(prompt_currency)

        text_parts = [
            "💱 <b>Обмен</b>",
            f"💨 {safe_receive_type}",
            f"💱 Курс для обмена: <b>{safe_display_rate}</b> (зафиксирован)",
        ]
        if safe_network_text:
            text_parts.append(safe_network_text)
        text_parts.extend([
            "💰 Мин. сумма для обмена без доп. комиссии: 10000 THB",
            "(Если сумма к получению &lt; 10000 THB, будет добавлена комиссия 300 THB к сумме, которую вы отдаете)",
            f"<b>❕ Введите сумму {safe_prompt_currency}:</b>"
        ])
        text = "\n\n".join(text_parts)

        await safe_edit_text(
            callback_query.message,
            text,
            reply_markup=reply_markup_val,
            parse_mode="HTML"
        )
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Ошибка в switch_input_currency_handler: {str(e)}")
        await callback_query.answer("Произошла ошибка. Попробуйте снова.")


# @router.message(StateFilter(None), F.text.regexp(r'^\d+([\.,]\d+)?$'))
# async def handle_amount_input(message: types.Message, state: FSMContext):
#     try:
#         data = await state.get_data()
#         currency_from = data.get("currency_from")
#         if not currency_from:
#             logging.info(f"Получена сумма '{message.text}' от {get_user_display(message.from_user)} вне контекста FSM.")
#             return
#
#         fixed_rate_for_calculation_str = data.get("exchange_rate_str")
#         if not fixed_rate_for_calculation_str:
#             logging.error(
#                 f"Критическая ошибка: exchange_rate_str не найден в FSM для {message.from_user.id} на этапе ввода суммы.")
#             await message.answer("Произошла ошибка: курс для расчета не определен. Пожалуйста, начните обмен заново.",
#                                  reply_markup=get_main_keyboard())
#             await state.clear()
#             return
#
#         current_rate_for_calc = float(fixed_rate_for_calculation_str)
#
#         amount_str = message.text.replace(',', '.')
#         amount_entered = float(amount_str)
#         user_tg_id = message.from_user.id
#
#         receive_type = data.get("receive_type", "Не указан")
#         currency_to = data.get("currency_to")
#         input_type = data.get("input_type")
#
#         amount_to_give = 0.0
#         amount_to_get = 0.0
#         final_commission_text = ""
#         MIN_THB_FOR_NO_COMMISSION = 10000.0
#         COMMISSION_THB_AMOUNT = 300.0
#         display_rate_text_for_deal = ""
#
#         if currency_from == "USDT":
#             display_rate_text_for_deal = f"1 USDT = {current_rate_for_calc:.2f} THB"
#             if input_type == "input_thb":
#                 amount_to_get = amount_entered
#                 amount_to_give = amount_to_get / current_rate_for_calc
#                 if amount_to_get < MIN_THB_FOR_NO_COMMISSION and amount_to_get > 0:
#                     commission_in_usdt = COMMISSION_THB_AMOUNT / current_rate_for_calc
#                     amount_to_give += commission_in_usdt
#                     final_commission_text = f"\n(включая комиссию {COMMISSION_THB_AMOUNT:.0f} THB ≈ {commission_in_usdt:.2f} USDT)"
#             else:
#                 amount_to_give_initial = amount_entered
#                 amount_to_get_calculated = amount_to_give_initial * current_rate_for_calc
#                 amount_to_give = amount_to_give_initial
#                 amount_to_get = amount_to_get_calculated
#                 if amount_to_get_calculated < MIN_THB_FOR_NO_COMMISSION and amount_to_get_calculated > 0:
#                     commission_in_usdt = COMMISSION_THB_AMOUNT / current_rate_for_calc
#                     amount_to_give += commission_in_usdt
#                     final_commission_text = f"\n(включая комиссию {COMMISSION_THB_AMOUNT:.0f} THB ≈ {commission_in_usdt:.2f} USDT)"
#
#         elif currency_from == "RUB":
#             display_rate_text_for_deal = f"1 RUB = {current_rate_for_calc:.4f} THB"
#             if input_type == "input_thb":
#                 amount_to_get = amount_entered
#                 amount_to_give = amount_to_get / current_rate_for_calc
#                 if amount_to_get < MIN_THB_FOR_NO_COMMISSION and amount_to_get > 0:
#                     commission_in_rub = COMMISSION_THB_AMOUNT / current_rate_for_calc
#                     amount_to_give += commission_in_rub
#                     final_commission_text = f"\n(включая комиссию {COMMISSION_THB_AMOUNT:.0f} THB ≈ {commission_in_rub:.2f} RUB)"
#             else:
#                 amount_to_give_initial = amount_entered
#                 amount_to_get_calculated = amount_to_give_initial * current_rate_for_calc
#                 amount_to_give = amount_to_give_initial
#                 amount_to_get = amount_to_get_calculated
#                 if amount_to_get_calculated < MIN_THB_FOR_NO_COMMISSION and amount_to_get_calculated > 0:
#                     commission_in_rub = COMMISSION_THB_AMOUNT / current_rate_for_calc
#                     amount_to_give += commission_in_rub
#                     final_commission_text = f"\n(включая комиссию {COMMISSION_THB_AMOUNT:.0f} THB ≈ {commission_in_rub:.2f} RUB)"
#
#         if amount_to_get <= 0 or amount_to_give <= 0:
#             await message.answer("Сумма обмена слишком мала. Пожалуйста, введите большую сумму.")
#             return
#
#         new_request_in_db = await db.create_exchange_request(
#             tg_id=user_tg_id,
#             currency_from=currency_from,
#             currency_to=currency_to,
#             give=round(amount_to_give, 8 if currency_from == "USDT" else 2),
#             rate=fixed_rate_for_calculation_str,
#             get=round(amount_to_get, 2),
#         )
#
#         if not new_request_in_db:
#             await message.answer("Произошла ошибка при создании заявки. Попробуйте позже.",
#                                  reply_markup=get_main_keyboard())
#             await state.clear()
#             return
#
#         request_id = new_request_in_db.id
#
#         await state.update_data(
#             request_id=request_id,
#             final_amount_to_give=amount_to_give,
#             final_amount_to_get=amount_to_get,
#             final_commission_text=final_commission_text
#         )
#
#         safe_receive_type = html.escape(receive_type)
#         safe_display_rate = html.escape(display_rate_text_for_deal)
#         safe_currency_from = html.escape(currency_from)
#         safe_commission_text = html.escape(final_commission_text)
#         safe_currency_to = html.escape(currency_to if currency_to else "THB")  # На случай если currency_to не "THB"
#
#         text_to_confirm = (
#             "💱 <b>Проверьте детали обмена</b>\n\n"
#             f"💌 Заявка №{request_id}\n"
#             f"💨 {safe_receive_type}\n"
#             f"💱 Курс: <b>{safe_display_rate}</b> (зафиксирован для этой сделки)\n"
#             f"💸 Вы отдаёте: <b>{amount_to_give:.2f} {safe_currency_from}</b>{safe_commission_text}\n"
#             f"💰 Получаете: <b>{amount_to_get:.2f} {safe_currency_to}</b>\n\n"
#             "❕<b>Подтвердите заявку:</b>"
#         )
#         await message.answer(
#             text_to_confirm,
#             reply_markup=inline_keyboards.get_confirm_exchange_keyboard(),
#             parse_mode="HTML"
#         )
#     except ValueError:
#         await message.answer("Пожалуйста, введите корректную сумму.")
#     except Exception as e:
#         logging.exception(f"Критическая ошибка в handle_amount_input:")
#         await message.answer("Произошла непредвиденная ошибка при обработке суммы. Мы уже разбираемся.")

@router.message(StateFilter(None), F.text.regexp(r'^\d+([\.,]\d+)?$'))
async def handle_amount_input(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        currency_from = data.get("currency_from")
        if not currency_from:
            logging.info(f"Получена сумма '{message.text}' от {get_user_display(message.from_user)} вне контекста FSM.")
            return

        # Используем зафиксированный (и уже скорректированный на RATE_ADJUSTMENT_PERCENTAGE) курс из FSM
        fixed_adjusted_rate_str = data.get("exchange_rate_str")
        if not fixed_adjusted_rate_str:
            logging.error(
                f"Критическая ошибка: exchange_rate_str не найден в FSM для {message.from_user.id} на этапе ввода суммы.")
            await message.answer("Произошла ошибка: курс для расчета не определен. Пожалуйста, начните обмен заново.",
                                 reply_markup=get_main_keyboard())
            await state.clear()
            return

        # Это ваш курс обмена (уже с учетом 10% "дельты")
        exchange_rate_for_calc = float(fixed_adjusted_rate_str)

        amount_str = message.text.replace(',', '.')
        amount_entered_by_user = float(amount_str)  # Сумма, которую ввел пользователь
        user_tg_id = message.from_user.id

        receive_type = data.get("receive_type", "Не указан")
        currency_to = data.get("currency_to")  # Должен быть "THB"
        input_type = data.get("input_type")  # Какую валюту вводил пользователь

        # Переменные для финальных сумм
        final_amount_to_give_by_user = 0.0  # Сколько пользователь в итоге отдаст (включая возможную мин. комиссию)
        final_amount_to_get_by_user = 0.0  # Сколько пользователь в итоге получит (уже с вычетом всех комиссий)

        min_commission_text = ""  # Текст про минимальную комиссию (300 THB)
        exchanger_fee_thb = 0.0  # Сумма комиссии обменника в THB
        exchanger_fee_text = ""  # Текст про комиссию обменника

        # --- Шаг 1: Расчет предварительных сумм без комиссии обменника, но с учетом минимальной комиссии ---
        preliminary_amount_to_give = 0.0
        preliminary_amount_to_get_thb = 0.0  # Сумма в THB до вычета комиссии обменника

        if currency_from == "USDT":
            if input_type == "input_thb":  # Пользователь ввел, сколько THB хочет получить
                preliminary_amount_to_get_thb = amount_entered_by_user
                preliminary_amount_to_give = preliminary_amount_to_get_thb / exchange_rate_for_calc
                if preliminary_amount_to_get_thb < MIN_THB_FOR_NO_COMMISSION and preliminary_amount_to_get_thb > 0:
                    commission_equivalent_give = MIN_COMMISSION_THB / exchange_rate_for_calc
                    preliminary_amount_to_give += commission_equivalent_give
                    min_commission_text = f"\n(включая доп. сбор {MIN_COMMISSION_THB:.0f} THB ≈ {commission_equivalent_give:.2f} {currency_from} за малую сумму)"
            else:  # input_usdt. Пользователь ввел, сколько USDT хочет отдать
                preliminary_amount_to_give_initial = amount_entered_by_user
                preliminary_amount_to_get_thb_calculated = preliminary_amount_to_give_initial * exchange_rate_for_calc

                preliminary_amount_to_give = preliminary_amount_to_give_initial
                preliminary_amount_to_get_thb = preliminary_amount_to_get_thb_calculated

                if preliminary_amount_to_get_thb_calculated < MIN_THB_FOR_NO_COMMISSION and preliminary_amount_to_get_thb_calculated > 0:
                    commission_equivalent_give = MIN_COMMISSION_THB / exchange_rate_for_calc
                    preliminary_amount_to_give += commission_equivalent_give
                    min_commission_text = f"\n(включая доп. сбор {MIN_COMMISSION_THB:.0f} THB ≈ {commission_equivalent_give:.2f} {currency_from} за малую сумму)"
                    # Сумма к получению (preliminary_amount_to_get_thb) не меняется от этой мин. комиссии,
                    # т.к. мы увеличили сумму к отдаче.

        elif currency_from == "RUB":
            if input_type == "input_thb":
                preliminary_amount_to_get_thb = amount_entered_by_user
                preliminary_amount_to_give = preliminary_amount_to_get_thb / exchange_rate_for_calc
                if preliminary_amount_to_get_thb < MIN_THB_FOR_NO_COMMISSION and preliminary_amount_to_get_thb > 0:
                    commission_equivalent_give = MIN_COMMISSION_THB / exchange_rate_for_calc
                    preliminary_amount_to_give += commission_equivalent_give
                    min_commission_text = f"\n(включая доп. сбор {MIN_COMMISSION_THB:.0f} THB ≈ {commission_equivalent_give:.2f} {currency_from} за малую сумму)"
            else:  # input_rub
                preliminary_amount_to_give_initial = amount_entered_by_user
                preliminary_amount_to_get_thb_calculated = preliminary_amount_to_give_initial * exchange_rate_for_calc

                preliminary_amount_to_give = preliminary_amount_to_give_initial
                preliminary_amount_to_get_thb = preliminary_amount_to_get_thb_calculated

                if preliminary_amount_to_get_thb_calculated < MIN_THB_FOR_NO_COMMISSION and preliminary_amount_to_get_thb_calculated > 0:
                    commission_equivalent_give = MIN_COMMISSION_THB / exchange_rate_for_calc
                    preliminary_amount_to_give += commission_equivalent_give
                    min_commission_text = f"\n(включая доп. сбор {MIN_COMMISSION_THB:.0f} THB ≈ {commission_equivalent_give:.2f} {currency_from} за малую сумму)"

        if preliminary_amount_to_get_thb <= 0 or preliminary_amount_to_give <= 0:
            await message.answer("Сумма обмена слишком мала. Пожалуйста, введите большую сумму.")
            return

        # --- Шаг 2: Применение комиссии обменника (EXCHANGER_FEE_PERCENTAGE) ---
        # Комиссия берется от суммы THB, которую пользователь получил бы без этой комиссии
        exchanger_fee_thb = preliminary_amount_to_get_thb * EXCHANGER_FEE_PERCENTAGE
        final_amount_to_get_by_user = preliminary_amount_to_get_thb - exchanger_fee_thb

        # Текст про комиссию обменника (если она есть)
        #if exchanger_fee_thb > 0.005:  # Показываем, если комиссия хотя бы полкопейки бата
         #   exchanger_fee_text = f"\nКомиссия обменника: {exchanger_fee_thb:.2f} THB ({EXCHANGER_FEE_PERCENTAGE * 100:.1f}%)"

        final_amount_to_give_by_user = preliminary_amount_to_give  # Сумма к отдаче не меняется от комиссии обменника (по Варианту 1)

        # Итоговый текст с деталями комиссий
        all_commission_details_text = min_commission_text  # Сначала текст про мин. комиссию (если была)
        # if min_commission_text and exchanger_fee_text: # Если обе комиссии
        #     all_commission_details_text += " и " + exchanger_fee_text.lstrip('\n') # Убираем лишний перенос строки
        # elif exchanger_fee_text: # Если только комиссия обменника
        #     all_commission_details_text = exchanger_fee_text
        # Более простой вариант: просто конкатенируем, если они есть
        if exchanger_fee_text:
            all_commission_details_text += exchanger_fee_text

        # --- Шаг 3: Формирование текста для отображения и запись в БД ---
        display_rate_text_for_deal = ""
        if currency_from == "USDT":
            display_rate_text_for_deal = f"1 USDT = {exchange_rate_for_calc:.2f} THB"
        elif currency_from == "RUB":
            display_rate_text_for_deal = f"1 RUB = {exchange_rate_for_calc:.4f} THB"

        new_request_in_db = await db.create_exchange_request(
            tg_id=user_tg_id,
            currency_from=currency_from,
            currency_to=currency_to,  # THB
            give=round(final_amount_to_give_by_user, 8 if currency_from == "USDT" else 2),
            rate=fixed_adjusted_rate_str,  # Это ваш "скорректированный на 10%" курс
            get=round(final_amount_to_get_by_user, 2),  # Это итоговая сумма с учетом всех комиссий
        )

        if not new_request_in_db:
            await message.answer("Произошла ошибка при создании заявки. Попробуйте позже.",
                                 reply_markup=get_main_keyboard())
            await state.clear()
            return

        request_id = new_request_in_db.id

        # Сохраняем в FSM финальные суммы для использования на следующих шагах
        await state.update_data(
            request_id=request_id,
            final_amount_to_give=final_amount_to_give_by_user,  # Это то, что пользователь отдаст
            final_amount_to_get=final_amount_to_get_by_user,  # Это то, что пользователь получит
            final_commission_text=all_commission_details_text  # Общий текст про все комиссии
            # exchange_rate_str (ваш скорректированный курс) уже в FSM
        )

        safe_receive_type = html.escape(receive_type)
        safe_display_rate = html.escape(display_rate_text_for_deal)  # Это ваш скорректированный курс
        safe_currency_from = html.escape(currency_from)
        safe_commission_details_text = html.escape(all_commission_details_text)
        safe_currency_to = html.escape(str(currency_to))

        text_to_confirm = (
            "💱 <b>Проверьте детали обмена</b>\n\n"
            f"💌 Заявка №{request_id}\n"
            f"💨 {safe_receive_type}\n"
            f"💱 Наш курс (до комиссии обменника): <b>{safe_display_rate}</b>\n"
            f"💸 Вы отдаёте: <b>{final_amount_to_give_by_user:.2f} {safe_currency_from}</b>{safe_commission_details_text}\n"
            f"💰 Вы получите (после всех комиссий): <b>{final_amount_to_get_by_user:.2f} {safe_currency_to}</b>\n\n"
            "❕<b>Подтвердите заявку:</b>"
        )
        await message.answer(
            text_to_confirm,
            reply_markup=inline_keyboards.get_confirm_exchange_keyboard(),
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму.")
    except Exception as e:
        logging.exception("Критическая ошибка в handle_amount_input:")
        await message.answer("Произошла непредвиденная ошибка при обработке суммы. Мы уже разбираемся.")

@router.callback_query(F.data == "confirm_exchange")
async def confirm_exchange_handler(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        request_id = data.get("request_id")
        currency_from = data.get("currency_from")
        amount_to_give = data.get("final_amount_to_give")
        amount_to_get = data.get("final_amount_to_get")

        if not all([request_id, currency_from, amount_to_give is not None, amount_to_get is not None]):
            await callback_query.answer("Ошибка: не удалось получить данные заявки. Пожалуйста, начните заново.",
                                        show_alert=True)
            # ... (код для ответа пользователю, если edit_text не сработал) ...
            await state.clear()
            return

        await db.update_exchange_request_data(request_id=request_id, status=db.Status.pending_payment)

        payment_details_text = ""
        if currency_from == "USDT":
            payment_details_text = (
                "💳 <b>Реквизиты для оплаты:</b>\n\n"
                f"💸 Сумма к оплате: <b>{amount_to_give:.2f} USDT</b>\n"
                f"💰 Вы получите: <b>{amount_to_get:.2f} THB</b>\n\n"
                "📝 <b>USDT (TRC20)</b>\n"
                "Кошелек: <code>ВАШ_USDT_КОШЕЛЕК_TRC20</code>\n"  # ЗАМЕНИТЬ
                "Сеть: TRC20\n\n"
                "⚠️ После оплаты, пожалуйста, отправьте скриншот подтверждения перевода в этот чат."
            )
        elif currency_from == "RUB":
            payment_details_text = (
                "💳 <b>Реквизиты для оплаты:</b>\n\n"
                f"💸 Сумма к оплате: <b>{amount_to_give:.2f} RUB</b>\n"
                f"💰 Вы получите: <b>{amount_to_get:.2f} THB</b>\n\n"
                "📝 <b>Рублевый перевод</b>\n"
                "Номер: <code>ВАШ_НОМЕР_КАРТЫ_ИЛИ_ТЕЛЕФОНА</code>\n"  # ЗАМЕНИТЬ
                "Банки: Сбербанк, Альфа, Тинькофф (или ваши банки)\n"
                "Получатель: ИМЯ ФАМИЛИЯ ПОЛУЧАТЕЛЯ\n\n"  # ЗАМЕНИТЬ
                "⚠️ После оплаты, пожалуйста, отправьте скриншот подтверждения перевода в этот чат."
            )

        await safe_edit_text(
            callback_query.message,
            payment_details_text,
            reply_markup=inline_keyboards.get_cancel_exchange_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state("waiting_for_payment_screenshot")
        await callback_query.answer()

    except Exception as e:
        logging.error("Ошибка в confirm_exchange_handler: {str(e)}")
        await callback_query.answer("Произошла ошибка. Попробуйте снова.")


@router.message(F.photo, StateFilter("waiting_for_payment_screenshot"))
async def handle_payment_screenshot(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        user_tg_id = message.from_user.id
        username = message.from_user.username or f"id{user_tg_id}"

        request_id = data.get("request_id")
        receive_type = data.get("receive_type", "Не указан")
        currency_from = data.get("currency_from")
        currency_to = data.get("currency_to")
        amount_to_give = data.get("final_amount_to_give")
        amount_to_get = data.get("final_amount_to_get")
        actual_rate_str = data.get("exchange_rate_str")  # Зафиксированный курс
        final_commission_text = data.get("final_commission_text", "")

        if not request_id:
            logging.error(f"Критическая ошибка: request_id не найден в FSM для {user_tg_id} при отправке скриншота.")
            await message.answer("Произошла внутренняя ошибка. Пожалуйста, свяжитесь с поддержкой.",
                                 reply_markup=get_main_keyboard())
            await state.clear()
            return

        await db.update_exchange_request_data(request_id=request_id, status=db.Status.processing)

        safe_username = html.escape(username)
        safe_currency_from = html.escape(currency_from)
        safe_currency_to = html.escape(currency_to)
        safe_receive_type = html.escape(receive_type)
        safe_actual_rate_str = html.escape(actual_rate_str)
        safe_commission_text = html.escape(final_commission_text)

        text_for_manager = (
            f"💌 Новая заявка #{request_id} ожидает обработки!\n\n"
            f"💨 Пользователь: @{safe_username} (tg_id: {user_tg_id})\n"
            f"💱 Направление: {safe_currency_from} → {safe_currency_to}\n"
            f"🏦 Способ получения: {safe_receive_type}\n"
            f"Курс: 1 {safe_currency_from} = {safe_actual_rate_str} {safe_currency_to}\n"
            f"💸 Отдал: {amount_to_give:.2f} {safe_currency_from}{safe_commission_text}\n"
            f"💰 К получению: {amount_to_get:.2f} {safe_currency_to}\n"
        )

        # Отправляем скриншот и текст менеджеру
        # Сначала фото, потом текст с кнопками
        await message.bot.send_photo(
            chat_id=MANAGER_CHAT_ID,
            photo=message.photo[-1].file_id,
            # caption=text_for_manager, # Можно добавить caption к фото, но тогда кнопки будут под ним
            # reply_markup=inline_keyboards.get_manager_action_keyboard(request_id)
        )
        await message.bot.send_message(
            chat_id=MANAGER_CHAT_ID,
            text=text_for_manager,
            reply_markup=inline_keyboards.get_manager_action_keyboard(str(request_id))
            # request_id должен быть строкой для f-строки в клавиатуре
        )

        await message.answer(
            "✅ Ваш платеж получен и заявка отправлена на обработку менеджеру! Ожидайте дальнейших инструкций.\n\n"
            "Если возникнут какие-либо вопросы, с вами свяжется менеджер.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()

    except Exception as e:
        logging.exception("Ошибка при обработке скриншота оплаты:")
        await message.answer("Произошла ошибка при обработке вашего платежа. Пожалуйста, свяжитесь с поддержкой.",
                             reply_markup=get_main_keyboard())
        await state.clear()


@router.callback_query(F.data.startswith("manager_confirm_"))
async def handle_manager_confirm(callback_query: types.CallbackQuery):
    try:
        request_id_str = callback_query.data.split("_")[-1]
        request_id = int(request_id_str)

        exchange_request = await db.get_exchange_request_by_id(request_id)  # Эта функция должна загружать user
        if not exchange_request or not hasattr(exchange_request, 'user') or not exchange_request.user:
            await callback_query.answer(f"Заявка #{request_id} или данные пользователя не найдены.", show_alert=True)
            await safe_edit_text(callback_query.message,
                                 f"{callback_query.message.text}\n\n⚠️ Заявка #{request_id} или пользователь не найден!",
                                 reply_markup=None)
            return

        user_id_to_notify = exchange_request.user.tg_id

        await db.update_exchange_request_data(request_id=request_id, status=db.Status.pending_get)

        edited_manager_text = f"{callback_query.message.text}\n\n✅ Заявка #{request_id} подтверждена. Ожидается подтверждение получения от пользователя."
        await safe_edit_text(callback_query.message, edited_manager_text, reply_markup=None)

        await callback_query.bot.send_message(
            user_id_to_notify,
            f"✅ Ваша заявка #{request_id} подтверждена менеджером! Средства готовы к выдаче."
        )

        message_text_for_manager = callback_query.message.text  # Текст исходного сообщения менеджеру
        receive_type_from_text = "Не определен"  # Значение по умолчанию
        # Ищем способ получения в тексте сообщения (этот способ не самый надежный, лучше хранить в БД)
        if "Способ получения: Получение в отеле" in message_text_for_manager:
            receive_type_from_text = "Получение в отеле"
        elif "Способ получения: Получение в банкомате" in message_text_for_manager:
            receive_type_from_text = "Получение в банкомате"

        if receive_type_from_text == "Получение в отеле":
            await callback_query.bot.send_message(
                user_id_to_notify,
                "🏨 <b>Инструкция по получению в отеле:</b>\n\n"
                "1. Придите по адресу: <a href='https://maps.app.goo.gl/YUBKHTMEw29DJby18'>Отель \"Название Отеля\"</a>\n"  # ЗАМЕНИТЬ
                "2. Покажите на рецепшене это сообщение или ваш ID заявки.\n"
                "3. Получите ваши средства.",
                parse_mode="HTML"
            )
        elif receive_type_from_text == "Получение в банкомате":
            video_dir = "Video"
            if os.path.exists(video_dir) and os.path.isdir(video_dir):
                for video_file in sorted(os.listdir(video_dir)):  # sorted для порядка
                    if video_file.lower().endswith(('.mp4', '.avi', '.mov')):
                        video_path = os.path.join(video_dir, video_file)
                        try:
                            await callback_query.bot.send_video(user_id_to_notify, FSInputFile(video_path))
                        except Exception as e_vid:
                            logging.error(f"Ошибка отправки видео {video_path}: {e_vid}")
            else:
                logging.warning(f"Папка с видео '{video_dir}' не найдена.")

            pictures_dir = "pictures"
            for i in range(1, 3):
                image_path = os.path.join(pictures_dir, f"{i}.jpg")
                if os.path.exists(image_path):
                    try:
                        await callback_query.bot.send_photo(user_id_to_notify, FSInputFile(image_path))
                    except Exception as e_img:
                        logging.error(f"Ошибка отправки изображения {image_path}: {e_img}")
                else:
                    logging.warning(f"Изображение-инструкция {image_path} не найдено.")

        await callback_query.bot.send_message(
            user_id_to_notify,
            f"Пожалуйста, подтвердите получение средств по заявке #{request_id}:",
            reply_markup=inline_keyboards.get_receipt_confirmation_keyboard(request_id)
        )
        await callback_query.answer()

    except Exception as e:
        logging.exception(
            f"Ошибка при подтверждении заявки менеджером (request_id: {callback_query.data.split('_')[-1]}):")
        await callback_query.answer("Произошла ошибка при подтверждении. Попробуйте снова.")


@router.callback_query(F.data.startswith("manager_reject_"))
async def handle_manager_reject(callback_query: types.CallbackQuery):
    try:
        request_id_str = callback_query.data.split("_")[-1]
        request_id = int(request_id_str)

        exchange_request = await db.get_exchange_request_by_id(request_id)
        if not exchange_request or not hasattr(exchange_request, 'user') or not exchange_request.user:
            await callback_query.answer(f"Заявка #{request_id} или данные пользователя не найдены.", show_alert=True)
            # ... (можно отредактировать сообщение менеджеру об ошибке)
            return

        user_tg_id_to_notify = exchange_request.user.tg_id
        user_username_to_contact = html.escape(str(exchange_request.user.username or f"id{user_tg_id_to_notify}"))

        await db.update_exchange_request_data(request_id=request_id, status=db.Status.cancelled)

        edited_manager_text = f"{callback_query.message.text}\n\n❌ Заявка #{request_id} отклонена."
        await safe_edit_text(callback_query.message, edited_manager_text, reply_markup=None)

        await callback_query.bot.send_message(
            user_tg_id_to_notify,
            f"❌ Ваша заявка #{request_id} была отклонена менеджером. "
            "Пожалуйста, свяжитесь с поддержкой для уточнения деталей или ожидайте сообщения от менеджера."
        )

        await callback_query.bot.send_message(
            MANAGER_CHAT_ID,
            f"⚠️ Заявка #{request_id} отклонена. Пожалуйста, свяжитесь с пользователем @{user_username_to_contact} для уточнения деталей."
        )
        await callback_query.answer("Заявка отклонена.")

    except Exception as e:
        logging.exception(
            f"Ошибка при отклонении заявки менеджером (request_id: {callback_query.data.split('_')[-1]}):")
        await callback_query.answer("Произошла ошибка при отклонении. Попробуйте снова.")


@router.callback_query(F.data.startswith("receipt_confirmed_"))
async def handle_receipt_confirmation(callback_query: types.CallbackQuery):
    try:
        prefix = "receipt_confirmed_"
        request_id_str = callback_query.data[len(prefix):]
        request_id = int(request_id_str)

        updated_request = await db.update_exchange_request_data(request_id=request_id, status=db.Status.successful)

        if updated_request:
            logging.info(
                f"User {callback_query.from_user.id} confirmed receipt for request {request_id}. Status: {updated_request.status.value}")
            await safe_edit_text(
                callback_query.message,
                f"✅ Спасибо за подтверждение получения для заявки #{request_id}! Обмен успешно завершен.",
                reply_markup=None
            )
            await callback_query.bot.send_message(MANAGER_CHAT_ID,
                                                  f"✅ Пользователь подтвердил получение по заявке #{request_id}. Обмен завершен.")
        else:
            logging.warning(
                f"Не удалось найти или обновить заявку {request_id} при подтверждении получения пользователем {callback_query.from_user.id}.")
            await callback_query.answer("Не удалось обновить статус заявки. Свяжитесь с поддержкой.", show_alert=True)

        await callback_query.answer()
    except ValueError:
        logging.error(f"Не удалось извлечь ID из callback_data: {callback_query.data} в handle_receipt_confirmation")
        await callback_query.answer("Ошибка в данных кнопки.", show_alert=True)
    except Exception as e:
        logging.exception(f"Ошибка при подтверждении получения пользователем (callback_data: {callback_query.data}):")
        await callback_query.answer("Произошла ошибка. Попробуйте снова.")


@router.callback_query(F.data.startswith("support_contact_"))
async def handle_support_contact(callback_query: types.CallbackQuery):
    try:
        prefix = "support_contact_"
        request_id_str = callback_query.data[len(prefix):]
        request_id = int(request_id_str)

        await safe_edit_text(
            callback_query.message,
            "👨‍💼 Свяжитесь с поддержкой: @ВАШ_САППОРТ_ЮЗЕРНЕЙМ\n\n"  # ЗАМЕНИТЬ
            f"Пожалуйста, укажите номер вашей заявки: #{request_id}\n\n"
            "Вы можете вернуться к подтверждению получения средств:",
            reply_markup=inline_keyboards.get_receipt_confirmation_keyboard(request_id)
        )
        await callback_query.answer()
    except ValueError:
        logging.error(f"Не удалось извлечь ID из callback_data: {callback_query.data} в handle_support_contact")
        await callback_query.answer("Ошибка в данных кнопки.", show_alert=True)
    except Exception as e:
        logging.exception(f"Ошибка при запросе поддержки (callback_data: {callback_query.data}):")
        await callback_query.answer("Произошла ошибка. Попробуйте снова.")


@router.callback_query(F.data == "cancel_exchange")
async def cancel_exchange_handler(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        request_id = data.get("request_id")

        if request_id:
            updated_request = await db.update_exchange_request_data(request_id=request_id, status=db.Status.cancelled)
            if updated_request:
                logging.info(
                    f"User {callback_query.from_user.id} cancelled exchange request {request_id}. Status set to Cancelled.")
            else:
                logging.warning(
                    f"User {callback_query.from_user.id} tried to cancel request {request_id}, but it was not found or update failed.")
        else:
            logging.info(
                f"User {callback_query.from_user.id} cancelled exchange before request was created in DB (request_id is None).")

        await state.clear()

        try:
            await safe_edit_text(
                callback_query.message,
                "❌ Обмен отменен.\n\n💨 Выберите валюту, которую вы желаете получить, чтобы начать новый обмен:",
                reply_markup=inline_keyboards.get_exchange_main_keyboard()
            )
        except Exception:
            await callback_query.message.answer(
                "❌ Обмен отменен.\n\n💨 Выберите валюту, которую вы желаете получить, чтобы начать новый обмен:",
                reply_markup=inline_keyboards.get_exchange_main_keyboard()
            )
        await callback_query.answer("Обмен отменен.")
    except Exception as e:
        logging.exception(f"Ошибка при отмене обмена пользователем:")
        await callback_query.answer("Произошла ошибка при отмене. Попробуйте снова.")


@router.callback_query(F.data == "history_exchanges")
async def show_exchange_history_handler(callback_query: types.CallbackQuery):
    try:
        user_tg_id = callback_query.from_user.id
        user_role = await db.get_user_role(tg_id=user_tg_id)

        history_text_header = "📜 <b>История обменов:</b>\n\n"
        history_text_body = ""
        exchanges_to_display = []
        reply_markup_history = None

        if user_role == db.Role.client:
            user_history = await db.get_user_exchange_history(tg_id=user_tg_id, include_creation_status=True)
            exchanges_to_display = user_history[:10]  # Последние 10
            if not exchanges_to_display:
                history_text_body = "У вас пока нет истории обменов."  # Без тегов, т.к. header уже с тегами
            reply_markup_history = inline_keyboards.get_profile_main_user_keyboard()

        elif user_role in [db.Role.admin, db.Role.manager]:
            all_history = await db.get_last_20_all_users_exchange_history()  # Уже содержит user
            exchanges_to_display = all_history
            if not exchanges_to_display:
                history_text_body = "В системе пока нет обменов."
            # reply_markup_history для админа можно оставить None или добавить свою админскую "назад"

        else:  # Неизвестная роль или None
            await callback_query.answer("Не удалось определить вашу роль для отображения истории.", show_alert=True)
            return

        if exchanges_to_display:
            for item in exchanges_to_display:
                user_info_for_admin = ""
                if user_role in [db.Role.admin, db.Role.manager] and hasattr(item, 'user') and item.user:
                    safe_username = html.escape(str(item.user.username or 'N/A'))
                    user_info_for_admin = f"👤 Пользователь: {item.user.tg_id} (@{safe_username})\n"

                safe_currency_from = html.escape(str(item.currency_from))
                safe_currency_to = html.escape(str(item.currency_to))
                rate_value_str = str(item.rate)
                safe_rate_display_str = html.escape(rate_value_str)
                safe_status_value = html.escape(str(item.status.value))

                rate_line = f"Курс: 1 {safe_currency_from} = {safe_rate_display_str} {safe_currency_to}" \
                    if item.rate and rate_value_str.lower() != "n/a" else "Курс: на момент сделки"

                history_text_body += (
                    f"<b>Заявка #{item.id}</b>\n"
                    f"{user_info_for_admin}"
                    f"🗓 Дата: {item.date.strftime('%Y-%m-%d %H:%M')}\n"
                    f"Направление: {safe_currency_from} → {safe_currency_to}\n"
                    f"💸 Отдал: {item.give:.2f} {safe_currency_from}\n"
                    f"💰 Получил: {item.get:.2f} {safe_currency_to}\n"
                    f"{rate_line}\n"
                    f"Статус: {safe_status_value}\n\n"
                )

        # Собираем итоговый текст
        final_history_text = history_text_header
        if history_text_body:  # Если есть тело истории (записи или сообщение "нет истории")
            final_history_text += history_text_body
        elif not exchanges_to_display:  # Если тело пустое и не было записей (на всякий случай, хотя должно быть заполнено выше)
            final_history_text += "Нет данных для отображения."

        await safe_edit_text(
            callback_query.message,
            final_history_text.strip(),
            reply_markup=reply_markup_history,
            parse_mode="HTML"
        )
        await callback_query.answer()

    except Exception as e:
        logging.exception(f"Ошибка при показе истории обменов:")
        await callback_query.answer("Произошла ошибка при загрузке истории. Попробуйте снова.")


async def safe_edit_text(message: types.Message, text: str, **kwargs):
    try:
        await message.edit_text(text, **kwargs)
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            logging.error(
                f"Ошибка при edit_text: {str(e)}. Сообщение: ID={message.message_id}, ChatID={message.chat.id}, Text: {text[:100]}")


@router.callback_query(F.data == "back_to_profile")
async def back_to_profile_handler(callback_query: types.CallbackQuery):
    try:
        tg_id = callback_query.from_user.id
        user_history = await db.get_user_exchange_history(tg_id=tg_id, include_creation_status=False)
        successful_exchanges_count = sum(1 for item in user_history if item.status == db.Status.successful)

        await safe_edit_text(
            callback_query.message,
            f"💢Ваш профиль💢\n\n"
            f"💫Ваш id: {tg_id}\n"
            f"💫Количество успешных обменов: {successful_exchanges_count} 🎈🎈\n",
            reply_markup=inline_keyboards.get_profile_main_user_keyboard()
        )
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Ошибка в back_to_profile_handler: {str(e)}")
        await callback_query.answer("Произошла ошибка.")
