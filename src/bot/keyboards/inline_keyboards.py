from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_exchange_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="THB", callback_data="exchange_usdt_or_rub")]
        ]
    )

def get_usdt_rub_directions_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="USDT → THB", callback_data="usdt_to_thb")],
            [InlineKeyboardButton(text="RUB → THB", callback_data="rub_to_thb")],
            [InlineKeyboardButton(text="Назад", callback_data="exchange_main")]
        ]
    )

def get_exchange_type_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Получить в банкомате", callback_data="exchange_in_ATM")],
            [InlineKeyboardButton(text="Получить в отеле", callback_data="exchange_in_hotel")],
            [InlineKeyboardButton(text="Назад", callback_data="exchange_usdt_or_rub")]
        ]
    )

def get_usdt_to_thb_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Указать сумму в валюте THB", callback_data="enter_thb_amount")],
            [InlineKeyboardButton(text="Назад", callback_data="usdt_to_thb")]
        ]
    )

def get_thb_to_usdt_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Указать сумму в валюте USDT", callback_data="enter_usdt_amount")],
            [InlineKeyboardButton(text="Назад", callback_data="usdt_to_thb")]
        ]
    )

def get_exchange_type_keyboard_rub_to_thb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Получить в банкомате", callback_data="exchange_in_ATM_rub")],
            [InlineKeyboardButton(text="Получить в отеле", callback_data="exchange_in_hotel_rub")],
            [InlineKeyboardButton(text="Назад", callback_data="exchange_usdt_or_rub")]
        ]
    )

def get_rub_to_thb_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Указать сумму в валюте THB", callback_data="enter_thb_amount_rub")],
            [InlineKeyboardButton(text="Назад", callback_data="rub_to_thb")]
        ]
    )

def get_thb_to_rub_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Указать сумму в валюте RUB", callback_data="enter_rub_amount")],
            [InlineKeyboardButton(text="Назад", callback_data="rub_to_thb")]
        ]
    )

def get_profile_main_user_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="История обменов", callback_data="history_exchanges")],
            [InlineKeyboardButton(text="Оставить отзыв", url="https://t.me/+w1iU4eQUG_oyYTIy")],
            [InlineKeyboardButton(text="Поддержка", callback_data="support_main")]
        ]
    )

def get_confirm_exchange_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подтвердить", callback_data="confirm_exchange")],
            [InlineKeyboardButton(text="Отменить", callback_data="cancel_exchange")]
        ]
    )

def get_cancel_exchange_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="❌ Отменить обмен", callback_data="cancel_exchange")
    return keyboard.as_markup()

def get_manager_action_keyboard(request_id: str):
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Подтвердить", callback_data=f"manager_confirm_{request_id}")
    keyboard.button(text="❌ Отклонить", callback_data=f"manager_reject_{request_id}")
    return keyboard.as_markup()

def get_receipt_confirmation_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Получил", callback_data="receipt_confirmed")
    keyboard.button(text="❓ Связаться с поддержкой", callback_data="support_contact")
    return keyboard.as_markup()

