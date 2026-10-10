"""Telegram bot: savolni API'ga yuboradi va javobni ko'rsatadi.

Ishlatish:  python -m app.bot   (avval API ishga tushgan bo'lishi kerak)
"""

import asyncio
import html
import logging

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.config import settings

logger = logging.getLogger(__name__)
dp = Dispatcher()
api = httpx.AsyncClient(base_url=settings.api_url, timeout=30)

WELCOME = (
    "Assalomu alaykum! Davlat xizmatlari bo'yicha savolingizni o'z so'zlaringiz bilan yozing.\n\n"
    "Masalan: <i>ID-karta necha kunda tayyor bo'ladi?</i>"
)
NOT_FOUND = (
    "Kechirasiz, bu savol bo'yicha ma'lumot topilmadi. "
    "Savolni boshqacha so'zlar bilan yozib ko'ring."
)
API_DOWN = "Xizmat vaqtincha ishlamayapti. Birozdan keyin qayta urinib ko'ring."


@dp.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(WELCOME)


@dp.message(F.text)
async def question(message: Message) -> None:
    try:
        resp = await api.post("/ask", json={"question": message.text})
        if resp.status_code == 422:
            await message.answer(
                "Savol juda qisqa yoki juda uzun. Iltimos, aniqroq yozing."
            )
            return
        resp.raise_for_status()
    except httpx.HTTPError:
        logger.exception("API bilan aloqa xatosi")
        await message.answer(API_DOWN)
        return

    data = resp.json()
    if data["status"] == "found":
        await message.answer(html.escape(data["matches"][0]["answer"]))
    elif data["status"] == "ambiguous":
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=m["matched_question"][:60],
                        callback_data=f"ans:{m['answer_id']}",
                    )
                ]
                for m in data["matches"]
            ]
        )
        await message.answer(
            "Savolingizni aniqlashtiring, qaysi biri?", reply_markup=keyboard
        )
    else:
        await message.answer(NOT_FOUND)


@dp.callback_query(F.data.startswith("ans:"))
async def pick_option(callback: CallbackQuery) -> None:
    answer_id = int(callback.data.split(":")[1])
    try:
        resp = await api.get(f"/answers/{answer_id}")
        resp.raise_for_status()
    except httpx.HTTPError:
        logger.exception("API bilan aloqa xatosi")
        await callback.answer(API_DOWN, show_alert=True)
        return
    await callback.message.answer(html.escape(resp.json()["answer"]))
    await callback.answer()


@dp.message()
async def other(message: Message) -> None:
    await message.answer("Iltimos, savolingizni matn ko'rinishida yozing.")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode="HTML"))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
