# -*- coding: utf-8 -*-
"""
Lazzatli uslubidagi taom yetkazib berish boti.
Ishga tushirish: python bot.py
Talab qilinadi: BOT_TOKEN, WEBAPP_URL (.env faylida)
"""

import asyncio
import json
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ContentType,
)
from dotenv import load_dotenv

from menu_data import MENU, DELIVERY_FEE, FREE_DELIVERY_THRESHOLD

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com/webapp/")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")  # buyurtmalar shu chatga tushadi
COMPANY_NAME = os.getenv("COMPANY_NAME", "Lazzatli")
MANAGER_PHONE = os.getenv("MANAGER_PHONE", "+998 90 000 00 00")

logging.basicConfig(level=logging.INFO)
router = Router()

# ------------------------------------------------------------------
# Juda oddiy "baza" - foydalanuvchi tili va telefon raqamini json faylda saqlaydi.
# Production uchun buni SQLite/Postgres bilan almashtirish tavsiya etiladi.
# ------------------------------------------------------------------
DB_FILE = "users.json"


def load_db() -> dict:
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_db(data: dict) -> None:
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user(user_id: int) -> dict:
    db = load_db()
    return db.get(str(user_id), {"lang": None, "phone": None, "orders": 0})


def set_user(user_id: int, **kwargs) -> None:
    db = load_db()
    user = db.get(str(user_id), {"lang": None, "phone": None, "orders": 0})
    user.update(kwargs)
    db[str(user_id)] = user
    save_db(db)


# ------------------------------------------------------------------
# Klaviaturalar
# ------------------------------------------------------------------

def lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")],
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        ]
    )


def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    menu_label = "🍽 Menyuni ochish" if lang == "uz" else "🍽 Открыть меню"
    phone_label = "📱 Raqamni ulashish" if lang == "uz" else "📱 Поделиться номером"
    lang_label = "🌐 Til / Язык"
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=menu_label, web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text=phone_label, request_contact=True)],
            [KeyboardButton(text=lang_label)],
        ],
        resize_keyboard=True,
    )


WELCOME_UZ = (
    "🍽 <b>{company}</b>ga xush kelibsiz!\n"
    "Onam tayyorlagandek mazali, issiq taomlar — to'g'ri eshigingizgacha 🤗\n\n"
    "🎁 <b>Sodiqlik dasturi:</b> har 5-chi kombo — BEPUL!\n"
    "🚚 Tez yetkazib berish · 🕐 10:00–17:00\n\n"
    "Boshlash uchun pastdagi 🍽 «Menyuni ochish» tugmasini bosing.\n"
    "Ballar yig'ish uchun raqamingizni ulashing 👇"
)

WELCOME_RU = (
    "🍽 Добро пожаловать в <b>{company}</b>!\n"
    "Вкусные горячие блюда, как готовит мама — прямо к вашей двери 🤗\n\n"
    "🎁 <b>Программа лояльности:</b> каждое 5-е комбо — БЕСПЛАТНО!\n"
    "🚚 Быстрая доставка · 🕐 10:00–17:00\n\n"
    "Нажмите кнопку 🍽 «Открыть меню», чтобы начать.\n"
    "Поделитесь номером, чтобы копить баллы 👇"
)

REMINDER_UZ = (
    "Hali ham tanlayapsizmi? 🍽\n"
    "Menyudan buyurtma bering yoki menejerga qo'ng'iroq qiling: <b>{phone}</b>\n"
    "Issiq, uyda pishirilgandek taomlar sizni kutyapti ❤️"
)

REMINDER_RU = (
    "Все еще выбираете? 🍽\n"
    "Оформите заказ через меню или позвоните менеджеру: <b>{phone}</b>\n"
    "Горячие, домашние блюда уже ждут вас ❤️"
)


# ------------------------------------------------------------------
# Handlerlar
# ------------------------------------------------------------------

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Tilni tanlang / Выберите язык:", reply_markup=lang_keyboard())


@router.callback_query(F.data.startswith("lang_"))
async def on_lang_chosen(callback):
    lang = callback.data.split("_")[1]  # uz | ru
    set_user(callback.from_user.id, lang=lang)

    confirm = "✅ Til o'zbekchaga o'rnatildi." if lang == "uz" else "✅ Язык переключен на русский."
    await callback.message.answer(confirm)

    welcome = WELCOME_UZ.format(company=COMPANY_NAME) if lang == "uz" else WELCOME_RU.format(company=COMPANY_NAME)
    await callback.message.answer(welcome, reply_markup=main_menu_keyboard(lang))

    reminder = REMINDER_UZ.format(phone=MANAGER_PHONE) if lang == "uz" else REMINDER_RU.format(phone=MANAGER_PHONE)
    await callback.message.answer(reminder)
    await callback.answer()


@router.message(F.text.in_(["🌐 Til / Язык"]))
async def change_lang(message: Message):
    await message.answer("Tilni tanlang / Выберите язык:", reply_markup=lang_keyboard())


@router.message(F.content_type == ContentType.CONTACT)
async def on_contact(message: Message):
    user = get_user(message.from_user.id)
    lang = user.get("lang") or "uz"
    set_user(message.from_user.id, phone=message.contact.phone_number)

    text = (
        "Rahmat! Raqamingiz saqlandi ✅ Endi ballar yig'a olasiz."
        if lang == "uz"
        else "Спасибо! Номер сохранён ✅ Теперь вы копите баллы."
    )
    await message.answer(text)


@router.message(F.web_app_data)
async def on_webapp_order(message: Message):
    """Mini-App (menyu) dan yuborilgan buyurtmani qabul qiladi."""
    user = get_user(message.from_user.id)
    lang = user.get("lang") or "uz"

    try:
        order = json.loads(message.web_app_data.data)
    except (ValueError, AttributeError):
        await message.answer("Xatolik: buyurtma o'qilmadi." if lang == "uz" else "Ошибка при чтении заказа.")
        return

    items = order.get("items", [])
    total = order.get("total", 0)

    lines_uz = [f"🧾 <b>Yangi buyurtma #{message.from_user.id}-{datetime.now().strftime('%H%M%S')}</b>"]
    lines_uz.append(f"👤 {message.from_user.full_name} (@{message.from_user.username or '-'})")
    if user.get("phone"):
        lines_uz.append(f"📞 {user['phone']}")
    lines_uz.append("")
    for it in items:
        lines_uz.append(f"• {it['name']} x{it['qty']} — {it['price'] * it['qty']:,} so'm".replace(",", " "))
    lines_uz.append("")
    lines_uz.append(f"💰 <b>Jami: {total:,} so'm</b>".replace(",", " "))

    order_text = "\n".join(lines_uz)

    # Foydalanuvchiga tasdiq
    confirm_uz = "✅ Buyurtmangiz qabul qilindi! Tez orada operatorimiz siz bilan bog'lanadi."
    confirm_ru = "✅ Ваш заказ принят! Наш оператор скоро свяжется с вами."
    await message.answer(confirm_uz if lang == "uz" else confirm_ru)

    # Admin/oshxonaga yuborish
    if ADMIN_CHAT_ID:
        try:
            await message.bot.send_message(ADMIN_CHAT_ID, order_text)
        except Exception as e:
            logging.warning(f"Adminga yuborilmadi: {e}")

    # Buyurtmalar sonini oshirish (sodiqlik dasturi uchun)
    set_user(message.from_user.id, orders=user.get("orders", 0) + 1)


@router.message()
async def fallback(message: Message):
    user = get_user(message.from_user.id)
    lang = user.get("lang")
    if not lang:
        await cmd_start(message)
        return
    await message.answer(
        "Pastdagi «Menyuni ochish» tugmasidan foydalaning 🍽"
        if lang == "uz"
        else "Используйте кнопку «Открыть меню» ниже 🍽",
        reply_markup=main_menu_keyboard(lang),
    )


async def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN topilmadi. .env faylini to'ldiring.")
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    # Boshqa tizim (masalan LeadTeh) shu tokenga webhook o'rnatgan bo'lishi mumkin.
    # Polling bilan ishlash uchun uni majburan tozalaymiz.
    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
