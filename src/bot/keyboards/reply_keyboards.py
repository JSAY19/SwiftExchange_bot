from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💰 Совершить обмен", callback_data="exchange_main"),
                KeyboardButton(text="👩‍💻 Профиль", callback_data="profile_main")
            ],
            [
                KeyboardButton(text="💸 Курсы обмена", callback_data="exchange_courses_main"),
                KeyboardButton(text="💬 Поддержка", callback_data="support_main")
            ]
        ],
        resize_keyboard=True
    )
    return keyboard