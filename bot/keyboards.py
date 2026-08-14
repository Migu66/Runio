"""Constructores de teclados."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from bot import texts


def main_menu() -> ReplyKeyboardMarkup:
    """Teclado persistente con las acciones del día a día."""
    rows = [[KeyboardButton(text=texts.BTN_PROFILE)]]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True)
