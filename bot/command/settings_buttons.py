from aiogram import types
from aiogram.types import InlineKeyboardButton
async def settings_command(message: types.Message) -> None:
    settings_markup = InlineKeyboardBuilder()
    settings_markup.button(
        text="Google",
        url="google.com"

    )
    settings_markup.button(
        text='Помощь',
        callback_data='help'

    )