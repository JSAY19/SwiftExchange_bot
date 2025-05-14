#-------------------- Импорты и константы - -------------------
from aiogram import Router, types, F
import aiohttp
import html
# Предполагаем, что CoinGeckoClient находится в src.services.coingecko_client (или укажите правильный путь)
# Проверьте, что путь импорта CoinGeckoClient верный
from src.services.CoinGecko import CoinGeckoClient  # ИЗМЕНЕНО: Путь к вашему клиенту
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

# Удаляем глобальные константы для курсов, они теперь будут в FSM
# USDT_TO_THB_RATE = 36.50
# RUB_TO_THB_RATE = 0.41

# Глобальные переменные для клиента API и сессии
# Инициализируются в on_startup
aiohttp_session_global: aiohttp.ClientSession | None = None
coingecko_client_global: CoinGeckoClient | None = None

# --- ID Менеджера (лучше вынести в конфиг) ---
MANAGER_CHAT_ID = 6659909595  # Пример

router = Router()


# -------------------- Вспомогательная функция для обновления курсов --------------------
async def update_and_store_rates_in_fsm(state: FSMContext, client: CoinGeckoClient | None = None) -> dict | None:
    """
    Получает актуальные курсы с CoinGecko и сохраняет их в FSM.
    Возвращает словарь с курсами или None в случае ошибки.
    """
    # Используем переданный клиент или глобальный, если не передан
    current_client = client if client else coingecko_client_global

    if not current_client:
        logging.error("CoinGeckoClient не инициализирован (ни передан, ни глобальный)!")
        await state.update_data(current_usdt_thb_rate=None, current_rub_thb_rate=None)
        return None

    try:
        rates = await current_client.get_rate()  # Ожидаем {'USDT/THB': ..., 'RUB/THB': ...}
        if rates and isinstance(rates, dict) and 'USDT/THB' in rates and 'RUB/THB' in rates:
            usdt_thb_rate = rates.get('USDT/THB')
            rub_thb_rate = rates.get('RUB/THB')

            await state.update_data(
                current_usdt_thb_rate=usdt_thb_rate,
                current_rub_thb_rate=rub_thb_rate,
                # Также сохраняем курс, который будет использован для сделки (фиксируем его)
                # Это будет сделано на этапе выбора направления
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

        output_path = "pictures/XchangerBot_bright.png"
        photo = FSInputFile(output_path)
        await message.answer_photo(
            photo=photo,
            caption="🏦 Мы предлагаем надёжные, оперативные и полностью автоматизированные услуги обмена российских рублей, USDT, THB.\n"
                    "💎 Приоритет №1 — качество нашего сервиса. Мы высоко ценим каждого нашего клиента и стремимся сделать процесс обмена максимально удобным и быстрым, чтобы Вы всегда возвращались к нам.\n"
                    "💬 → Техническая поддержка: @ТЕХ_ПОДДЕРЖКА",  # ЗАМЕНИТЬ
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
async def exchange_main_back(callback_query: types.CallbackQuery, state: FSMContext):  # Добавил state
    # При возврате в главное меню обмена, также обновим курсы
    actual_rates = await update_and_store_rates_in_fsm(state)
    if not actual_rates:
        await callback_query.answer("Не удалось обновить курсы. Попробуйте еще раз.", show_alert=True)
        # Можно вернуть пользователя на предыдущий шаг или в главное меню
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
        # Обновляем курсы на этом шаге
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

        data = await state.get_data()  # Получаем FSM data, где уже должен быть курс
        current_usdt_thb = data.get('current_usdt_thb_rate')

        if current_usdt_thb is None:  # Если вдруг курса нет, пытаемся обновить
            updated_rates = await update_and_store_rates_in_fsm(state)
            if not updated_rates or updated_rates.get('USDT/THB') is None:
                await callback_query.answer("Не удалось получить актуальный курс USDT/THB. Попробуйте позже.",
                                            show_alert=True)
                return
            current_usdt_thb = updated_rates.get('USDT/THB')

        # Фиксируем курс для этой конкретной сессии обмена
        await state.update_data(
            currency_from="USDT",
            currency_to="THB",
            exchange_rate_str=str(current_usdt_thb),  # Это курс, по которому будет сделка
            request_id=None
        )

        await safe_edit_text(
            callback_query.message,
            f"<b>💱 Выбор обмена (USDT → THB)</b>\n"
            f"Текущий курс для информации: <b>1 USDT ≈ {current_usdt_thb:.2f} THB</b>\n"
            f"(курс для обмена будет зафиксирован на этом шаге)\n\n"
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
            exchange_rate_str=str(current_rub_thb),  # Фиксируем курс для сделки
            request_id=None
        )

        await safe_edit_text(
            callback_query.message,
            f"<b>🎈Выбор обмена (RUB → THB)🎈</b>\n"
            f"Текущий курс для информации: <b>1 RUB ≈ {current_rub_thb:.4f} THB</b>\n"
            f"(курс для обмена будет зафиксирован на этом шаге)\n\n"
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

        if not fixed_rate_for_deal_str:  # Дополнительная проверка
            await callback_query.answer("Ошибка: курс для обмена не установлен. Попробуйте начать заново.",
                                        show_alert=True)
            return

        fixed_rate_for_deal_float = float(fixed_rate_for_deal_str)
        reply_markup_val = None
        prompt_currency = ""
        display_rate_text_for_deal = ""
        network_text = ""

        if currency_from == "USDT":
            display_rate_text_for_deal = f"1 USDT = {fixed_rate_for_deal_float:.2f} THB"
            if callback_query.data == "enter_thb_amount":
                await state.update_data(input_type="input_thb")
                prompt_currency = "THB, которую вы хотите получить"
                reply_markup_val = inline_keyboards.get_thb_to_usdt_keyboard()
            else:  # enter_usdt_amount
                await state.update_data(input_type="input_usdt")
                prompt_currency = "USDT, которую вы хотите обменять"
                reply_markup_val = inline_keyboards.get_usdt_to_thb_keyboard()
            network_text = "✔ Сеть: TRC20\n"

        elif currency_from == "RUB":
            display_rate_text_for_deal = f"1 RUB = {fixed_rate_for_deal_float:.4f} THB"
            if callback_query.data == "enter_thb_amount_rub":
                await state.update_data(input_type="input_thb")
                prompt_currency = "THB, которую вы хотите получить"
                reply_markup_val = inline_keyboards.get_thb_to_rub_keyboard()
            else:  # enter_rub_amount
                await state.update_data(input_type="input_rub")
                prompt_currency = "RUB, которую вы хотите обменять"
                reply_markup_val = inline_keyboards.get_rub_to_thb_keyboard()
            # network_text = "" # Уже инициализирован

        text = (
            "💱 <b>Обмен</b>\n\n"
            f"💨 {receive_type}\n"
            f"💱 Курс для обмена: <b>{display_rate_text_for_deal}</b> (зафиксирован)\n"
            f"{network_text}"
            "💰 Мин. сумма для обмена без доп. комиссии: 10000 THB\n"
            "(Если сумма к получению &lt; 10000 THB, будет добавлена комиссия 300 THB к сумме, которую вы отдаете)\n\n"
            f"<b>❕ Введите сумму {prompt_currency}:</b>"
        )

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


@router.message(StateFilter(None), F.text.regexp(r'^\d+([\.,]\d+)?$'))
async def handle_amount_input(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        currency_from = data.get("currency_from")
        if not currency_from:
            logging.info(f"Получена сумма '{message.text}' от {get_user_display(message.from_user)} вне контекста FSM.")
            return

        fixed_rate_for_calculation_str = data.get("exchange_rate_str")
        if not fixed_rate_for_calculation_str:
            logging.error(
                f"Критическая ошибка: exchange_rate_str не найден в FSM для {message.from_user.id} на этапе ввода суммы.")
            # Пытаемся аварийно обновить, но это не очень хорошо, т.к. пользователь видел другой курс.
            # Лучше прервать и попросить начать заново.
            await message.answer("Произошла ошибка: курс для расчета не определен. Пожалуйста, начните обмен заново.",
                                 reply_markup=get_main_keyboard())
            await state.clear()
            return

        current_rate_for_calc = float(fixed_rate_for_calculation_str)

        amount_str = message.text.replace(',', '.')
        amount_entered = float(amount_str)
        user_tg_id = message.from_user.id

        receive_type = data.get("receive_type", "Не указан")
        currency_to = data.get("currency_to")  # Должен быть "THB"
        input_type = data.get("input_type")

        amount_to_give = 0.0
        amount_to_get = 0.0
        final_commission_text = ""
        MIN_THB_FOR_NO_COMMISSION = 10000.0
        COMMISSION_THB_AMOUNT = 300.0
        display_rate_text_for_deal = ""  # Курс, по которому идет сделка

        if currency_from == "USDT":
            display_rate_text_for_deal = f"1 USDT = {current_rate_for_calc:.2f} THB"
            if input_type == "input_thb":  # Пользователь ввел THB (сколько хочет получить)
                amount_to_get = amount_entered
                amount_to_give = amount_to_get / current_rate_for_calc
                if amount_to_get < MIN_THB_FOR_NO_COMMISSION and amount_to_get > 0:  # Проверяем, что не 0
                    commission_in_usdt = COMMISSION_THB_AMOUNT / current_rate_for_calc
                    amount_to_give += commission_in_usdt
                    final_commission_text = f"\n(включая комиссию {COMMISSION_THB_AMOUNT:.0f} THB ≈ {commission_in_usdt:.2f} USDT)"
            else:  # input_usdt. Пользователь ввел USDT (сколько хочет отдать)
                amount_to_give_initial = amount_entered
                amount_to_get_calculated = amount_to_give_initial * current_rate_for_calc
                amount_to_give = amount_to_give_initial
                amount_to_get = amount_to_get_calculated  # Сначала считаем без комиссии
                if amount_to_get_calculated < MIN_THB_FOR_NO_COMMISSION and amount_to_get_calculated > 0:
                    commission_in_usdt = COMMISSION_THB_AMOUNT / current_rate_for_calc
                    amount_to_give += commission_in_usdt  # Пользователь отдает больше
                    # amount_to_get остается тем же, что был рассчитан от amount_to_give_initial,
                    # так как комиссия добавляется к сумме "отдаю"
                    final_commission_text = f"\n(включая комиссию {COMMISSION_THB_AMOUNT:.0f} THB ≈ {commission_in_usdt:.2f} USDT)"

        elif currency_from == "RUB":
            display_rate_text_for_deal = f"1 RUB = {current_rate_for_calc:.4f} THB"
            if input_type == "input_thb":
                amount_to_get = amount_entered
                amount_to_give = amount_to_get / current_rate_for_calc
                if amount_to_get < MIN_THB_FOR_NO_COMMISSION and amount_to_get > 0:
                    commission_in_rub = COMMISSION_THB_AMOUNT / current_rate_for_calc
                    amount_to_give += commission_in_rub
                    final_commission_text = f"\n(включая комиссию {COMMISSION_THB_AMOUNT:.0f} THB ≈ {commission_in_rub:.2f} RUB)"
            else:  # input_rub
                amount_to_give_initial = amount_entered
                amount_to_get_calculated = amount_to_give_initial * current_rate_for_calc
                amount_to_give = amount_to_give_initial
                amount_to_get = amount_to_get_calculated
                if amount_to_get_calculated < MIN_THB_FOR_NO_COMMISSION and amount_to_get_calculated > 0:
                    commission_in_rub = COMMISSION_THB_AMOUNT / current_rate_for_calc
                    amount_to_give += commission_in_rub
                    final_commission_text = f"\n(включая комиссию {COMMISSION_THB_AMOUNT:.0f} THB ≈ {commission_in_rub:.2f} RUB)"

        # Проверка на минимальную сумму обмена, если есть (например, не меньше 1 THB)
        if amount_to_get <= 0 or amount_to_give <= 0:
            await message.answer("Сумма обмена слишком мала. Пожалуйста, введите большую сумму.")
            return

        new_request_in_db = await db.create_exchange_request(
            tg_id=user_tg_id,
            currency_from=currency_from,
            currency_to=currency_to,
            give=round(amount_to_give, 8 if currency_from == "USDT" else 2),  # Точность для отдаваемой валюты
            rate=fixed_rate_for_calculation_str,
            get=round(amount_to_get, 2),
        )

        if not new_request_in_db:
            await message.answer("Произошла ошибка при создании заявки. Попробуйте позже.",
                                 reply_markup=get_main_keyboard())
            await state.clear()
            return

        request_id = new_request_in_db.id

        await state.update_data(
            request_id=request_id,
            final_amount_to_give=amount_to_give,
            final_amount_to_get=amount_to_get,
            final_commission_text=final_commission_text
        )

        text_to_confirm = (
            f"💱 <b>Проверьте детали обмена</b>\n\n"
            f"💌 Заявка №{request_id}\n"
            f"💨 {receive_type}\n"
            f"💱 Курс: <b>{display_rate_text_for_deal}</b> (зафиксирован для этой сделки)\n"
            f"💸 Вы отдаёте: <b>{amount_to_give:.2f} {currency_from}</b>{final_commission_text}\n"
            f"💰 Получаете: <b>{amount_to_get:.2f} {currency_to}</b>\n\n"
            f"❕<b>Подтвердите заявку:</b>"
        )
        await message.answer(
            text_to_confirm,
            reply_markup=inline_keyboards.get_confirm_exchange_keyboard(),
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму.")
    except Exception as e:
        logging.exception(f"Критическая ошибка в handle_amount_input:")  # Используем exception для полного трейсбека
        await message.answer("Произошла непредвиденная ошибка при обработке суммы. Мы уже разбираемся.")


# --- Остальные хендлеры (confirm_exchange_handler, handle_payment_screenshot и т.д.) остаются в основном такими же,
# так как они уже работают с request_id из FSM, который теперь будет корректно установлен ---

# ... (пропустил без изменений handle_payment_screenshot, manager_confirm, manager_reject, receipt_confirmation, support_contact, cancel_exchange, history, safe_edit, back_to_profile)
# Важно: в cancel_exchange_handler логика остается прежней.

# Код для `confirm_exchange_handler` (без изменений, т.к. он уже берет данные из FSM)
@router.callback_query(F.data == "confirm_exchange")
async def confirm_exchange_handler(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        request_id = data.get("request_id")
        currency_from = data.get("currency_from")
        amount_to_give = data.get("final_amount_to_give")  # Используем сохраненные финальные суммы
        amount_to_get = data.get("final_amount_to_get")

        if not all([request_id, currency_from, amount_to_give is not None, amount_to_get is not None]):
            await callback_query.answer("Ошибка: не удалось получить данные заявки. Пожалуйста, начните заново.",
                                        show_alert=True)
            current_message_id = callback_query.message.message_id
            try:
                await safe_edit_text(callback_query.message, "Произошла ошибка. Пожалуйста, начните обмен заново.",
                                     reply_markup=inline_keyboards.get_exchange_main_keyboard())
            except Exception:  # Если не удалось отредактировать, отправляем новое
                if callback_query.message.message_id == current_message_id:  # Чтобы не отправить, если уже отредактировано
                    await callback_query.message.answer("Произошла ошибка. Пожалуйста, начните обмен заново.",
                                                        reply_markup=inline_keyboards.get_exchange_main_keyboard())
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
                "Кошелек: <code>TMjRsz5SZ16adPMf11QQNZDHYkwQ58nSDd</code>\n"
                "Сеть: TRC20\n\n"
                "⚠️ После оплаты, пожалуйста, отправьте скриншот подтверждения перевода в этот чат."
            )
        elif currency_from == "RUB":
            payment_details_text = (
                "💳 <b>Реквизиты для оплаты:</b>\n\n"
                f"💸 Сумма к оплате: <b>{amount_to_give:.2f} RUB</b>\n"
                f"💰 Вы получите: <b>{amount_to_get:.2f} THB</b>\n\n"
                "📝 <b>Рублевый перевод</b>\n"
                "Номер: <code>+79263691059</code>\n"
                "Банки: Сбербанк, Альфа, Тинькофф\n"
                "Получатель: Виталий Водолазов\n\n"
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
        logging.error(f"Ошибка в confirm_exchange_handler: {str(e)}")
        await callback_query.answer("Произошла ошибка. Попробуйте снова.")


@router.callback_query(F.data == "history_exchanges")
async def show_exchange_history_handler(callback_query: types.CallbackQuery):
    try:
        user_tg_id = callback_query.from_user.id
        user_role = await db.get_user_role(tg_id=user_tg_id)

        history_text_header = "📜 <b>История обменов:</b>\n\n"
        history_text_body = ""  # Для элементов истории
        exchanges_to_display = []
        reply_markup_history = None

        if user_role == db.Role.client:
            user_history = await db.get_user_exchange_history(
                tg_id=user_tg_id,
                include_creation_status=True
            )
            exchanges_to_display = user_history[:10]
            if not exchanges_to_display:
                history_text_body = "📜 У вас пока нет истории обменов."
            reply_markup_history = inline_keyboards.get_profile_main_user_keyboard()

        elif user_role in [db.Role.admin, db.Role.manager]:
            all_history = await db.get_last_20_all_users_exchange_history()
            exchanges_to_display = all_history
            if not exchanges_to_display:
                history_text_body = "📜 В системе пока нет обменов."
            # reply_markup_history остается None для админа/менеджера (или можно задать свою)

        else:
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
                # Преобразуем item.rate в строку перед экранированием и проверкой
                rate_value_str = str(item.rate)
                safe_rate_display_str = html.escape(rate_value_str)
                safe_status_value = html.escape(str(item.status.value))  # item.status это Enum, .value это строка

                rate_line = f"Курс: 1 {safe_currency_from} = {safe_rate_display_str} {safe_currency_to}" \
                    if item.rate and rate_value_str.lower() != "n/a" else "Курс: на момент сделки"

                history_text_body += (
                    f"<b>Заявка #{item.id}</b>\n"
                    f"{user_info_for_admin}"
                    f"🗓 Дата: {item.date.strftime('%Y-%m-%d %H:%M')}\n"
                    f" направление: {safe_currency_from} → {safe_currency_to}\n"
                    f"💸 Отдал: {item.give:.2f} {safe_currency_from}\n"
                    f"💰 Получил: {item.get:.2f} {safe_currency_to}\n"
                    f"{rate_line}\n"
                    f" Статус: {safe_status_value}\n\n"
                )

        final_history_text = history_text_header + history_text_body if history_text_body else history_text_header + "Нет данных для отображения."
        if not exchanges_to_display and user_role == db.Role.client:  # Если для клиента нет истории
            final_history_text = "📜 У вас пока нет истории обменов."
        elif not exchanges_to_display and user_role in [db.Role.admin, db.Role.manager]:  # Если для админа нет истории
            final_history_text = "📜 В системе пока нет обменов."

        await safe_edit_text(
            callback_query.message,
            final_history_text.strip(),  # Убираем лишние пробелы в конце, если есть
            reply_markup=reply_markup_history,
            parse_mode="HTML"
        )
        await callback_query.answer()

    except Exception as e:
        logging.exception(f"Ошибка при показе истории обменов:")  # logging.exception для полного трейсбека
        await callback_query.answer("Произошла ошибка при загрузке истории. Попробуйте снова.")

async def safe_edit_text(message, *args, **kwargs):
    try:
        await message.edit_text(*args, **kwargs)
    except Exception as e:
        if "message is not modified" in str(e):
            pass  # Игнорируем эту ошибку
        else:
            logging.error(f"Ошибка при edit_text: {str(e)}")
            # Можно отправить ответ пользователю, если нужно