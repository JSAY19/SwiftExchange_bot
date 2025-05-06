from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_exchange_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="THB", callback_data="exchange_thb")]
        ]
    )

def get_usdt_directions_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="USDT → THB", callback_data="usdt_to_thb")],
            [InlineKeyboardButton(text="Назад", callback_data="exchange_main")]
        ]
    )

def get_exchange_type_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Получить в банкомате", callback_data="exchange_in_ATM")],
            [InlineKeyboardButton(text="Получить в отеле", callback_data="exchange_in_hotel")],
            [InlineKeyboardButton(text="Назад", callback_data="exchange_thb")]
        ]
    )