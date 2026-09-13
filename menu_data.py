# -*- coding: utf-8 -*-
"""
Kunlik menyu bilan ishlash.

Kafe konsepsiyasi: har kuni bir nechta (masalan 3 ta) taomdan iborat menyu.
Taomlar admin tomonidan botdagi buyruqlar orqali qo'shiladi/o'chiriladi —
GitHub yoki kodga tegishning hojati yo'q. Ma'lumot shu diskdagi
`daily_menu.json` faylida saqlanadi.
"""

import json
import os

DAILY_MENU_FILE = "daily_menu.json"

DELIVERY_FEE = 15000               # standart yetkazib berish narxi (so'm)
FREE_DELIVERY_THRESHOLD = 200000   # shu summadan yuqori bo'lsa yetkazib berish bepul
LOYALTY_EVERY_N_ORDER_FREE = 5     # har 5-chi buyurtmadan keyin mukofot


def load_daily_menu() -> list:
    """Hozirgi kunlik menyudagi taomlar ro'yxatini qaytaradi."""
    if os.path.exists(DAILY_MENU_FILE):
        with open(DAILY_MENU_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_daily_menu(items: list) -> None:
    with open(DAILY_MENU_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def add_dish(name: str, price: int, image: str, description: str = "") -> dict:
    items = load_daily_menu()
    new_id = f"dish_{len(items) + 1}_{int(price)}"
    dish = {
        "id": new_id,
        "nomi": name,
        "narx": price,
        "rasm": image,
        "tavsif": description,
    }
    items.append(dish)
    save_daily_menu(items)
    return dish


def remove_dish(index: int):
    """1-based index bo'yicha taomni o'chiradi."""
    items = load_daily_menu()
    if 1 <= index <= len(items):
        removed = items.pop(index - 1)
        save_daily_menu(items)
        return removed
    return None


def clear_menu() -> None:
    save_daily_menu([])
