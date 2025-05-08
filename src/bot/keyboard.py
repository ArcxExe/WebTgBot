from telegram import ReplyKeyboardMarkup, KeyboardButton

SESSION_START_BUTTON = "Начать сессию / Новый код"
SESSION_CLOSE_BUTTON = "Завершить сессию"

reply_keyboard = [
    [KeyboardButton(SESSION_START_BUTTON)],
    [KeyboardButton(SESSION_CLOSE_BUTTON)],
]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
