from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💰 Совершить обмен"),
                KeyboardButton(text="👩‍💻 Профиль")
            ],
            [
                KeyboardButton(text="💸 Курсы обмена"),
                KeyboardButton(text="💬 Поддержка")
            ]
        ]
    )
    return keyboard