from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💰 Совершить обмен", callback_data="exchange1"),
                KeyboardButton(text="👩‍💻 Профиль", callback_data="profile1")
            ],
            [
                KeyboardButton(text="💸 Курсы обмена", callback_data="exchange_courses1"),
                KeyboardButton(text="💬 Поддержка", callback_data="support1")
            ]
        ],
        resize_keyboard=True
    )
    return keyboard