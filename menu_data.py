# -*- coding: utf-8 -*-
"""
Do'kon menyusi (namuna ma'lumotlar).
Bu yerdagi narx, nom va rasmlarni o'zingizning haqiqiy taomlaringizga almashtiring.
Rasm uchun 'image' maydoniga to'g'ridan-to'g'ri internetdagi rasm havolasini (URL) qo'ying.
"""

MENU = {
    "kombo": {
        "name_uz": "Kombo",
        "name_ru": "Комбо",
        "items": [
            {
                "id": "kombo_1",
                "name_uz": "Spagetti + Salat kombosi",
                "name_ru": "Комбо спагетти + салат",
                "description_uz": "1. Taom  2. Salat",
                "price": 49000,
                "old_price": 65000,
                "image": "https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=600",
            },
        ],
    },
    "asosiy": {
        "name_uz": "Asosiy taomlar",
        "name_ru": "Основные блюда",
        "items": [
            {
                "id": "main_1",
                "name_uz": "Bifshteks (pishloq va pomidor bilan)",
                "name_ru": "Бифштекс (с сыром и помидором)",
                "price": 41000,
                "image": "https://images.unsplash.com/photo-1544025162-d76694265947?w=600",
            },
            {
                "id": "main_2",
                "name_uz": "Uyda pishirilgan kartoshka",
                "name_ru": "Домашняя жареная картошка",
                "price": 36000,
                "image": "https://images.unsplash.com/photo-1518013431117-eb1465fa5752?w=600",
            },
            {
                "id": "main_3",
                "name_uz": "Fo'sillon (go'shtli)",
                "name_ru": "Фучилон с мясом",
                "price": 38000,
                "image": "https://images.unsplash.com/photo-1612874742237-6526221588e3?w=600",
            },
            {
                "id": "main_4",
                "name_uz": "Kartoshka va kotletlar",
                "name_ru": "Картошка с котлетами",
                "price": 42000,
                "image": "https://images.unsplash.com/photo-1529042410759-befb1204b468?w=600",
            },
        ],
    },
    "garnir": {
        "name_uz": "Garnirlar",
        "name_ru": "Гарниры",
        "items": [
            {
                "id": "side_1",
                "name_uz": "Guruch",
                "name_ru": "Рис",
                "price": 18000,
                "image": "https://images.unsplash.com/photo-1516684732162-798a0062be99?w=600",
            },
            {
                "id": "side_2",
                "name_uz": "Grechka",
                "name_ru": "Гречка",
                "price": 18000,
                "image": "https://images.unsplash.com/photo-1586201375761-83865001e31c?w=600",
            },
            {
                "id": "side_3",
                "name_uz": "Kartoshka pyuresi",
                "name_ru": "Картофельное пюре",
                "price": 18000,
                "image": "https://images.unsplash.com/photo-1568569350062-ebfa3cb195df?w=600",
            },
            {
                "id": "side_4",
                "name_uz": "Qovurilgan kartoshka",
                "name_ru": "Жареная картошка",
                "price": 18000,
                "image": "https://images.unsplash.com/photo-1541592106381-b31e9677c0e5?w=600",
            },
            {
                "id": "side_5",
                "name_uz": "Mol go'shtli dolma",
                "name_ru": "Долма с говядиной",
                "price": 46000,
                "image": "https://images.unsplash.com/photo-1625944230945-1b7dd3b949ab?w=600",
            },
        ],
    },
    "salat": {
        "name_uz": "Salatlar",
        "name_ru": "Салаты",
        "items": [
            {
                "id": "salad_1",
                "name_uz": "Fasl salati",
                "name_ru": "Сезонный салат",
                "price": 22000,
                "image": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=600",
            },
            {
                "id": "salad_2",
                "name_uz": "Sezar salati",
                "name_ru": "Салат Цезарь",
                "price": 28000,
                "image": "https://images.unsplash.com/photo-1550304943-4f24f54ddde9?w=600",
            },
        ],
    },
}

DELIVERY_FEE = 15000          # standart yetkazib berish narxi (so'm)
FREE_DELIVERY_THRESHOLD = 200000  # shu summadan yuqori bo'lsa yetkazib berish bepul

LOYALTY_EVERY_N_ORDER_FREE = 5    # har 5-chi buyurtma/kombo bepul
