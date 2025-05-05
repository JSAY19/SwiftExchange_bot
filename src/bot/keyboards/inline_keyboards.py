from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_exchange_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="RUB", callback_data="exchange_rub")],
            [InlineKeyboardButton(text="THB", callback_data="exchange_thb")],
            [InlineKeyboardButton(text="USDT TRC20", callback_data="exchange_usdt")]
        ]
    )

def get_rub_directions_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="USDT → RUB", callback_data="usdt_to_rub")],
            [InlineKeyboardButton(text="THB → RUB", callback_data="thb_to_rub")],
            [InlineKeyboardButton(text="Назад", callback_data="exchange_main")]
        ]
    )

def get_thb_directions_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="RUB → THB", callback_data="rub_to_thb")],
            [InlineKeyboardButton(text="USDT → THB", callback_data="usdt_to_thb")],
            [InlineKeyboardButton(text="Назад", callback_data="exchange_main")]
        ]
    )

def get_usdt_directions_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="RUB → USDT", callback_data="rub_to_usdt")],
            [InlineKeyboardButton(text="THB → USDT", callback_data="thb_to_usdt")],
            [InlineKeyboardButton(text="Назад", callback_data="exchange_main")]
        ]
    )