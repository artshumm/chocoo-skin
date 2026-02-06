from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from app.core.config import settings

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    text = (
        "Chocoo Skin - Салон загара\n\n"
        "Добро пожаловать! Здесь вы можете записаться на сеанс загара."
    )

    if settings.mini_app_url:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Записаться",
                        web_app=WebAppInfo(url=settings.mini_app_url),
                    )
                ]
            ]
        )
        await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer(text + "\n\nMini App ещё не настроен.")
