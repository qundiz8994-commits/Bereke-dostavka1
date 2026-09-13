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

from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
    WebAppInfo,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ContentType,
)
from dotenv import load_dotenv

from menu_data import (
    load_daily_menu,
    save_daily_menu,
    add_dish,
    remove_dish,
    clear_menu,
    DELIVERY_FEE,
    FREE_DELIVERY_THRESHOLD,
    LOYALTY_EVERY_N_ORDER_FREE,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com/webapp/")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")  # buyurtmalar shu chatga tushadi
OWNER_ID = os.getenv("OWNER_ID", "")  # menyuni boshqara oladigan shaxsning Telegram ID'si
COMPANY_NAME = os.getenv("COMPANY_NAME", "Bereke")
MANAGER_PHONE = os.getenv("MANAGER_PHONE", "+998 97 356 89 94")
PORT = int(os.getenv("PORT", "8080"))

logging.basicConfig(level=logging.INFO)
router = Router()


def is_owner(user_id: int) -> bool:
    return OWNER_ID != "" and str(user_id) == str(OWNER_ID)


class OrderForm(StatesGroup):
    waiting_name = State()
    waiting_phone = State()
    waiting_address = State()
    waiting_comment = State()


class DishForm(StatesGroup):
    waiting_name = State()
    waiting_price = State()
    waiting_photo = State()
    waiting_desc = State()

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
    points_label = "🎁 Mening ballarim" if lang == "uz" else "🎁 Мои баллы"
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=menu_label, web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text=phone_label, request_contact=True)],
            [KeyboardButton(text=points_label)],
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
async def cmd_start(message: Message, state: FSMContext = None):
    if state:
        await state.clear()
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


@router.message(F.text == "/chatid")
async def get_chat_id(message: Message):
    await message.answer(f"Chat ID: <code>{message.chat.id}</code>")


@router.message(F.text.in_(["🎁 Mening ballarim", "🎁 Мои баллы"]))
async def my_points(message: Message):
    user = get_user(message.from_user.id)
    lang = user.get("lang") or "uz"
    orders = user.get("orders", 0)
    remainder = orders % LOYALTY_EVERY_N_ORDER_FREE
    left = LOYALTY_EVERY_N_ORDER_FREE - remainder if remainder != 0 else LOYALTY_EVERY_N_ORDER_FREE

    if lang == "uz":
        text = f"📊 Sizning jami buyurtmalaringiz: <b>{orders} ta</b>\n🎁 Yana <b>{left} ta</b> buyurtmadan so'ng — BEPUL kombo sizniki!"
    else:
        text = f"📊 Всего ваших заказов: <b>{orders}</b>\n🎁 Ещё <b>{left}</b> заказ(-ов) — и БЕСПЛАТНОЕ комбо ваше!"
    await message.answer(text)


@router.message(F.text.in_(["🌐 Til / Язык"]))
async def change_lang(message: Message):
    await message.answer("Tilni tanlang / Выберите язык:", reply_markup=lang_keyboard())


@router.message(F.content_type == ContentType.CONTACT, StateFilter(None))
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
async def on_webapp_order(message: Message, state: FSMContext):
    """Mini-App (menyu)dan faqat savatchani qabul qiladi, keyin ism/telefon/manzilni
    botning oddiy chat xabarlari orqali bir-bir so'raymiz — bu klaviatura bilan
    bog'liq muammolarning oldini oladi."""
    user = get_user(message.from_user.id)
    lang = user.get("lang") or "uz"

    try:
        cart = json.loads(message.web_app_data.data)
    except (ValueError, AttributeError):
        await message.answer("Xatolik: buyurtma o'qilmadi." if lang == "uz" else "Ошибка при чтении заказа.")
        return

    if not cart.get("items"):
        await message.answer("Savatcha bo'sh." if lang == "uz" else "Корзина пуста.")
        return

    await state.update_data(cart=cart)
    await state.set_state(OrderForm.waiting_name)

    text = "Ajoyib! Endi buyurtmani rasmiylashtiramiz.\n\n👤 Ismingizni yozing:" if lang == "uz" \
        else "Отлично! Оформим заказ.\n\n👤 Напишите ваше имя:"
    await message.answer(text, reply_markup=ReplyKeyboardRemove())


@router.message(StateFilter(OrderForm.waiting_name))
async def order_get_name(message: Message, state: FSMContext):
    user = get_user(message.from_user.id)
    lang = user.get("lang") or "uz"
    name = (message.text or "").strip()

    if not name:
        await message.answer("Iltimos, ismingizni matn ko'rinishida yozing." if lang == "uz" else "Пожалуйста, напишите имя текстом.")
        return

    await state.update_data(name=name)
    await state.set_state(OrderForm.waiting_phone)

    phone_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(
            text="📱 Raqamni yuborish" if lang == "uz" else "📱 Отправить номер",
            request_contact=True,
        )]],
        resize_keyboard=True,
    )
    text = "📞 Telefon raqamingizni yuboring (tugmani bosing yoki yozib yuboring):" if lang == "uz" \
        else "📞 Отправьте номер телефона (нажмите кнопку или напишите вручную):"
    await message.answer(text, reply_markup=phone_kb)


@router.message(StateFilter(OrderForm.waiting_phone))
async def order_get_phone(message: Message, state: FSMContext):
    user = get_user(message.from_user.id)
    lang = user.get("lang") or "uz"

    phone = message.contact.phone_number if message.contact else (message.text or "").strip()
    if not phone:
        await message.answer("Iltimos, telefon raqamingizni yuboring." if lang == "uz" else "Пожалуйста, отправьте номер телефона.")
        return

    set_user(message.from_user.id, phone=phone)
    await state.update_data(phone=phone)
    await state.set_state(OrderForm.waiting_address)

    text = "📍 Yetkazib berish manzilini yozing (ko'cha, uy, mo'ljal):" if lang == "uz" \
        else "📍 Напишите адрес доставки (улица, дом, ориентир):"
    await message.answer(text, reply_markup=ReplyKeyboardRemove())


@router.message(StateFilter(OrderForm.waiting_address))
async def order_get_address(message: Message, state: FSMContext):
    user = get_user(message.from_user.id)
    lang = user.get("lang") or "uz"
    address = (message.text or "").strip()

    if not address:
        await message.answer("Iltimos, manzilni matn ko'rinishida yozing." if lang == "uz" else "Пожалуйста, напишите адрес текстом.")
        return

    await state.update_data(address=address)
    await state.set_state(OrderForm.waiting_comment)

    text = "📝 Izoh qoldirmoqchimisiz? Bo'lmasa, shunchaki «-» deb yozing." if lang == "uz" \
        else "📝 Хотите оставить комментарий? Если нет — напишите «-»."
    await message.answer(text)


@router.message(StateFilter(OrderForm.waiting_comment))
async def order_get_comment(message: Message, state: FSMContext):
    user = get_user(message.from_user.id)
    lang = user.get("lang") or "uz"
    comment = (message.text or "").strip()
    if comment == "-":
        comment = ""

    data = await state.get_data()
    cart = data.get("cart", {})
    cust_name = data.get("name", "")
    cust_phone = data.get("phone", "")
    cust_address = data.get("address", "")

    items = cart.get("items", [])
    subtotal = cart.get("subtotal", 0)
    delivery = cart.get("delivery", 0)
    total = cart.get("total", 0)

    order_no = datetime.now().strftime("%d%m-%H%M%S")

    lines = [f"🧾 <b>YANGI BUYURTMA №{order_no}</b>", ""]
    lines.append(f"👤 <b>Mijoz:</b> {cust_name}")
    lines.append(f"📞 <b>Telefon:</b> {cust_phone}")
    lines.append(f"📍 <b>Manzil:</b> {cust_address}")
    if comment:
        lines.append(f"📝 <b>Izoh:</b> {comment}")
    lines.append("")
    lines.append("🍽 <b>Buyurtma tarkibi:</b>")
    for it in items:
        line_total = it["price"] * it["qty"]
        lines.append(f"  • {it['name']} — {it['qty']} dona × {it['price']:,} so'm = {line_total:,} so'm".replace(",", " "))
    lines.append("")
    lines.append(f"Mahsulotlar: {subtotal:,} so'm".replace(",", " "))
    delivery_text = "BEPUL" if delivery == 0 else f"{delivery:,} so'm".replace(",", " ")
    lines.append(f"Yetkazib berish: {delivery_text}")
    lines.append(f"💰 <b>JAMI: {total:,} so'm</b>".replace(",", " "))
    order_text = "\n".join(lines)

    # Sodiqlik dasturi
    new_order_count = user.get("orders", 0) + 1
    set_user(message.from_user.id, orders=new_order_count, name=cust_name)

    remainder = new_order_count % LOYALTY_EVERY_N_ORDER_FREE
    is_reward_order = remainder == 0
    left_to_reward = 0 if is_reward_order else LOYALTY_EVERY_N_ORDER_FREE - remainder

    if lang == "uz":
        confirm = f"✅ Buyurtmangiz qabul qilindi! Tez orada operatorimiz siz bilan bog'lanadi.\n\n📊 Bu — sizning <b>{new_order_count}-buyurtmangiz</b>!"
        confirm += "\n🎁 Tabriklaymiz! Siz BEPUL kombo yutdingiz — keyingi buyurtmangizda operatorga ayting!" if is_reward_order \
            else f"\n🎁 Yana <b>{left_to_reward} ta</b> buyurtmadan so'ng — BEPUL kombo sizniki!"
    else:
        confirm = f"✅ Ваш заказ принят! Наш оператор скоро свяжется с вами.\n\n📊 Это — ваш <b>{new_order_count}-й заказ</b>!"
        confirm += "\n🎁 Поздравляем! Вы выиграли БЕСПЛАТНОЕ комбо — сообщите об этом оператору в следующем заказе!" if is_reward_order \
            else f"\n🎁 Ещё <b>{left_to_reward}</b> заказ(-ов) — и БЕСПЛАТНОЕ комбо ваше!"

    await message.answer(confirm, reply_markup=main_menu_keyboard(lang))

    if ADMIN_CHAT_ID:
        try:
            admin_text = order_text + f"\n\n📊 Mijozning buyurtmalar soni: {new_order_count}"
            if is_reward_order:
                admin_text += "\n🎁 DIQQAT: mijoz sodiqlik mukofotiga (BEPUL kombo) haqli!"
            await message.bot.send_message(ADMIN_CHAT_ID, admin_text)
        except Exception as e:
            logging.warning(f"Adminga yuborilmadi: {e}")

    await state.clear()


@router.message(Command("yordam"))
async def admin_help(message: Message):
    if not is_owner(message.from_user.id):
        return
    text = (
        "🛠 <b>Admin buyruqlari:</b>\n\n"
        "/taom_qoshish — bugungi menyuga yangi taom qo'shish\n"
        "/taom_royxati — hozirgi kunlik menyuni ko'rish\n"
        "/taom_ochirish — ro'yxatdagi raqami bo'yicha taomni o'chirish\n"
        "/menu_tozalash — ertangi kun uchun butun menyuni tozalash"
    )
    await message.answer(text)


@router.message(Command("taom_qoshish"))
async def dish_add_start(message: Message, state: FSMContext):
    if not is_owner(message.from_user.id):
        return
    await state.set_state(DishForm.waiting_name)
    await message.answer("🍽 Taom nomini yozing:")


@router.message(StateFilter(DishForm.waiting_name))
async def dish_add_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer("Iltimos, taom nomini matn ko'rinishida yozing.")
        return
    await state.update_data(name=name)
    await state.set_state(DishForm.waiting_price)
    await message.answer("💰 Narxini yozing (faqat raqam, so'mda). Masalan: 35000")


@router.message(StateFilter(DishForm.waiting_price))
async def dish_add_price(message: Message, state: FSMContext):
    price_text = (message.text or "").strip().replace(" ", "")
    if not price_text.isdigit():
        await message.answer("Iltimos, narxni faqat raqam bilan yozing. Masalan: 35000")
        return
    await state.update_data(price=int(price_text))
    await state.set_state(DishForm.waiting_photo)
    await message.answer(
        "🖼 Taom rasmi uchun havola (URL) yuboring.\n"
        "Agar rasm bo'lmasa, «-» deb yozing."
    )


@router.message(StateFilter(DishForm.waiting_photo))
async def dish_add_photo(message: Message, state: FSMContext):
    photo = (message.text or "").strip()
    if photo == "-":
        photo = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600"
    await state.update_data(photo=photo)
    await state.set_state(DishForm.waiting_desc)
    await message.answer("📝 Qisqacha tavsif yozing (yoki «-»):")


@router.message(StateFilter(DishForm.waiting_desc))
async def dish_add_desc(message: Message, state: FSMContext):
    desc = (message.text or "").strip()
    if desc == "-":
        desc = ""

    data = await state.get_data()
    dish = add_dish(name=data["name"], price=data["price"], image=data["photo"], description=desc)
    await state.clear()

    await message.answer(
        f"✅ Qo'shildi!\n\n🍽 <b>{dish['nomi']}</b>\n💰 {dish['narx']:,} so'm".replace(",", " ")
    )


@router.message(Command("taom_royxati"))
async def dish_list(message: Message):
    if not is_owner(message.from_user.id):
        return
    items = load_daily_menu()
    if not items:
        await message.answer("Hozircha kunlik menyu bo'sh. /taom_qoshish orqali qo'shing.")
        return
    lines = ["📋 <b>Bugungi menyu:</b>\n"]
    for i, it in enumerate(items, start=1):
        lines.append(f"{i}. {it['nomi']} — {it['narx']:,} so'm".replace(",", " "))
    lines.append("\nO'chirish uchun: /taom_ochirish <raqam>")
    await message.answer("\n".join(lines))


@router.message(Command("taom_ochirish"))
async def dish_remove(message: Message):
    if not is_owner(message.from_user.id):
        return
    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Foydalanish: /taom_ochirish <raqam>\nRo'yxatni ko'rish uchun: /taom_royxati")
        return
    removed = remove_dish(int(parts[1]))
    if removed:
        await message.answer(f"🗑 O'chirildi: {removed['nomi']}")
    else:
        await message.answer("Bunday raqamli taom topilmadi.")


@router.message(Command("menu_tozalash"))
async def dish_clear(message: Message):
    if not is_owner(message.from_user.id):
        return
    clear_menu()
    await message.answer("🧹 Kunlik menyu tozalandi. Endi /taom_qoshish orqali yangi taomlarni qo'shing.")


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


async def menu_json_handler(request: web.Request) -> web.Response:
    items = load_daily_menu()
    data = {
        "taomlar": items,
        "yetkazib_berish": DELIVERY_FEE,
        "bepul_yetkazib_berish_dan": FREE_DELIVERY_THRESHOLD,
        "sana": datetime.now().strftime("%d.%m.%Y") + " kunlik menyu",
    }
    return web.json_response(
        data,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
        },
    )


async def menu_json_options(request: web.Request) -> web.Response:
    return web.Response(headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    })


async def start_web_server():
    app = web.Application()
    app.router.add_get("/menu.json", menu_json_handler)
    app.router.add_options("/menu.json", menu_json_options)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info(f"Menu API http://0.0.0.0:{PORT}/menu.json manzilida ishga tushdi")


async def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN topilmadi. .env faylini to'ldiring.")
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    # Boshqa tizim (masalan LeadTeh) shu tokenga webhook o'rnatgan bo'lishi mumkin.
    # Polling bilan ishlash uchun uni majburan tozalaymiz.
    await bot.delete_webhook(drop_pending_updates=True)

    await start_web_server()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
