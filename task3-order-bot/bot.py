"""
Telegram Order Bot — Кафе «Шафран», г. Алматы
Бот для приёма заказов с корзиной, оформлением и уведомлением админа.
aiogram 3.x (Router pattern)
"""

import os
import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ──────────────────────────────────────────────
# Конфигурация
# ──────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "8938709080:AAGwx1BxPRLecyv-UF-XvoVK90ji4kJwWIA")
ADMIN_CHAT_ID = 841509225  # Telegram ID администратора

CAFE_NAME = "Шафран"
CAFE_CITY = "Алматы"

# ──────────────────────────────────────────────
# Меню (категория → список товаров)
# ──────────────────────────────────────────────
MENU: dict[str, list[dict]] = {
    "🍔 Бургеры": [
        {"name": "Классический бургер", "price": 1800},
        {"name": "Чизбургер Делюкс", "price": 2200},
        {"name": "Острый Чикен бургер", "price": 2500},
        {"name": "Двойной Шафран бургер", "price": 3500},
    ],
    "🍕 Пицца": [
        {"name": "Маргарита", "price": 2500},
        {"name": "Пепперони", "price": 3200},
        {"name": "Четыре сыра", "price": 3800},
        {"name": "Мясная BBQ", "price": 4500},
    ],
    "🥗 Салаты": [
        {"name": "Цезарь с курицей", "price": 2200},
        {"name": "Греческий салат", "price": 1500},
        {"name": "Тёплый салат с говядиной", "price": 2800},
    ],
    "🥤 Напитки": [
        {"name": "Американо", "price": 800},
        {"name": "Капучино", "price": 1000},
        {"name": "Свежевыжатый сок", "price": 1200},
        {"name": "Лимонад домашний", "price": 500},
    ],
    "🍰 Десерты": [
        {"name": "Чизкейк Нью-Йорк", "price": 1800},
        {"name": "Тирамису", "price": 1600},
        {"name": "Шоколадный фондан", "price": 900},
    ],
}

# Глобальный счётчик заказов
order_counter = 0

# ──────────────────────────────────────────────
# FSM States
# ──────────────────────────────────────────────
class OrderState(StatesGroup):
    main_menu = State()
    category = State()
    item = State()
    cart = State()
    checkout_name = State()
    checkout_phone = State()
    checkout_type = State()
    checkout_address = State()
    confirm = State()

# ──────────────────────────────────────────────
# Router
# ──────────────────────────────────────────────
router = Router()

# ──────────────────────────────────────────────
# Вспомогательные функции
# ──────────────────────────────────────────────

def main_menu_kb() -> ReplyKeyboardMarkup:
    """Главное меню (reply-кнопки)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Меню"), KeyboardButton(text="🛒 Корзина")],
            [KeyboardButton(text="📞 Контакты"), KeyboardButton(text="ℹ️ О нас")],
        ],
        resize_keyboard=True,
    )


def categories_kb() -> InlineKeyboardMarkup:
    """Inline-кнопки категорий."""
    buttons = [
        [InlineKeyboardButton(text=cat, callback_data=f"cat:{cat}")]
        for cat in MENU
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def items_kb(category: str) -> InlineKeyboardMarkup:
    """Inline-кнопки товаров в категории."""
    items = MENU[category]
    buttons = [
        [InlineKeyboardButton(
            text=f"{item['name']} — {item['price']}₸",
            callback_data=f"item:{category}:{i}",
        )]
        for i, item in enumerate(items)
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ К категориям", callback_data="back_to_categories")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def item_detail_kb(category: str, idx: int) -> InlineKeyboardMarkup:
    """Кнопки на экране товара: добавить в корзину / назад."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 В корзину", callback_data=f"add:{category}:{idx}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"cat:{category}")],
    ])


def cart_kb(cart: list[dict]) -> InlineKeyboardMarkup:
    """Inline-кнопки корзины с +/- и удалением."""
    buttons = []
    for i, entry in enumerate(cart):
        buttons.append([InlineKeyboardButton(
            text=f"{entry['name']}  x{entry['qty']}  =  {entry['price'] * entry['qty']}₸",
            callback_data="noop",
        )])
        buttons.append([
            InlineKeyboardButton(text="➖", callback_data=f"cart_minus:{i}"),
            InlineKeyboardButton(text=f"{entry['qty']} шт.", callback_data="noop"),
            InlineKeyboardButton(text="➕", callback_data=f"cart_plus:{i}"),
            InlineKeyboardButton(text="🗑", callback_data=f"cart_del:{i}"),
        ])
    total = sum(e["price"] * e["qty"] for e in cart)
    buttons.append([InlineKeyboardButton(text=f"💰 Итого: {total}₸", callback_data="noop")])
    buttons.append([
        InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout"),
        InlineKeyboardButton(text="🗑 Очистить", callback_data="cart_clear"),
    ])
    buttons.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def delivery_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚗 Доставка", callback_data="dtype:delivery")],
        [InlineKeyboardButton(text="🏪 Самовывоз", callback_data="dtype:pickup")],
    ])


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="order_confirm"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="order_cancel"),
        ],
    ])


def format_cart_text(cart: list[dict]) -> str:
    if not cart:
        return "🛒 Корзина пуста."
    lines = ["🛒 <b>Ваша корзина:</b>\n"]
    total = 0
    for i, e in enumerate(cart, 1):
        subtotal = e["price"] * e["qty"]
        total += subtotal
        lines.append(f"{i}. {e['name']} × {e['qty']} = {subtotal}₸")
    lines.append(f"\n💰 <b>Итого: {total}₸</b>")
    return "\n".join(lines)


def format_order_for_admin(data: dict, order_num: int, user_id: int, username: str | None) -> str:
    """Форматированное сообщение для админа."""
    cart = data["cart"]
    total = sum(e["price"] * e["qty"] for e in cart)
    items_text = "\n".join(
        f"  • {e['name']} × {e['qty']} = {e['price'] * e['qty']}₸"
        for e in cart
    )
    dtype = "🚗 Доставка" if data.get("delivery_type") == "delivery" else "🏪 Самовывоз"
    address_line = f"\n📍 Адрес: {data['address']}" if data.get("address") else ""
    user_link = f"@{username}" if username else f"id:{user_id}"

    return (
        f"🔔 <b>Новый заказ #{order_num}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 Имя: {data['name']}\n"
        f"📱 Телефон: {data['phone']}\n"
        f"🆔 Telegram: {user_link}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{items_text}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 Итого: {total}₸\n"
        f"{dtype}{address_line}\n"
        f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )


# ──────────────────────────────────────────────
# Handlers
# ──────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await state.update_data(cart=[])
    await message.answer(
        f"👋 Добро пожаловать в кафе <b>«{CAFE_NAME}»</b>, г. {CAFE_CITY}!\n\n"
        "Выберите действие из меню ниже 👇",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )
    await state.set_state(OrderState.main_menu)


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🤖 <b>Команды бота:</b>\n"
        "/start — Перезапуск бота\n"
        "/help — Справка\n\n"
        "Используйте кнопки меню для навигации.",
        parse_mode="HTML",
    )


# ── Главное меню (reply-кнопки) ──

@router.message(F.text == "📋 Меню")
async def show_menu(message: Message, state: FSMContext):
    await message.answer("📋 Выберите категорию:", reply_markup=categories_kb(), parse_mode="HTML")
    await state.set_state(OrderState.category)


@router.message(F.text == "🛒 Корзина")
async def show_cart_reply(message: Message, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", [])
    if not cart:
        await message.answer("🛒 Корзина пуста.\nОткройте 📋 Меню, чтобы добавить блюда.", parse_mode="HTML")
        return
    await message.answer(format_cart_text(cart), reply_markup=cart_kb(cart), parse_mode="HTML")
    await state.set_state(OrderState.cart)


@router.message(F.text == "📞 Контакты")
async def show_contacts(message: Message):
    await message.answer(
        f"📞 <b>Кафе «{CAFE_NAME}»</b>\n\n"
        f"📍 г. {CAFE_CITY}\n"
        "☎️ +7 (727) 123-45-67\n"
        "🕐 Пн-Вс: 10:00 — 22:00\n"
        "📸 Instagram: @cafe_yantar",
        parse_mode="HTML",
    )


@router.message(F.text == "ℹ️ О нас")
async def show_about(message: Message):
    await message.answer(
        f"ℹ️ <b>Кафе «{CAFE_NAME}»</b> — уютное место в центре {CAFE_CITY}.\n\n"
        "Мы готовим из свежих продуктов каждый день.\n"
        "Бургеры, пицца, салаты, десерты и авторские напитки.\n\n"
        "Доставка по городу 🚗 | Самовывоз 🏪",
        parse_mode="HTML",
    )


# ── Каталог: категории → товары → детали ──

@router.callback_query(F.data.startswith("cat:"))
async def cb_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":", 1)[1]
    await callback.message.edit_text(
        f"<b>{category}</b>\nВыберите блюдо:",
        reply_markup=items_kb(category),
        parse_mode="HTML",
    )
    await state.set_state(OrderState.item)
    await callback.answer()


@router.callback_query(F.data == "back_to_categories")
async def cb_back_to_categories(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📋 Выберите категорию:",
        reply_markup=categories_kb(),
        parse_mode="HTML",
    )
    await state.set_state(OrderState.category)
    await callback.answer()


@router.callback_query(F.data == "back_to_menu")
async def cb_back_to_menu(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        f"Кафе <b>«{CAFE_NAME}»</b> — выберите действие в меню ниже 👇",
        parse_mode="HTML",
    )
    await state.set_state(OrderState.main_menu)
    await callback.answer()


@router.callback_query(F.data.startswith("item:"))
async def cb_item_detail(callback: CallbackQuery, state: FSMContext):
    _, category, idx_str = callback.data.split(":", 2)
    idx = int(idx_str)
    item = MENU[category][idx]
    await callback.message.edit_text(
        f"<b>{item['name']}</b>\n\n💰 Цена: {item['price']}₸",
        reply_markup=item_detail_kb(category, idx),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("add:"))
async def cb_add_to_cart(callback: CallbackQuery, state: FSMContext):
    _, category, idx_str = callback.data.split(":", 2)
    idx = int(idx_str)
    item = MENU[category][idx]

    data = await state.get_data()
    cart: list[dict] = data.get("cart", [])

    # Если товар уже в корзине — увеличиваем количество
    for entry in cart:
        if entry["name"] == item["name"]:
            entry["qty"] += 1
            await state.update_data(cart=cart)
            await callback.answer(f"✅ {item['name']} — теперь {entry['qty']} шт.")
            return

    cart.append({"name": item["name"], "price": item["price"], "qty": 1})
    await state.update_data(cart=cart)
    await callback.answer(f"✅ {item['name']} добавлен в корзину!")


# ── Корзина ──

@router.callback_query(F.data.startswith("cart_plus:"))
async def cb_cart_plus(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    cart: list[dict] = data.get("cart", [])
    if idx < len(cart):
        cart[idx]["qty"] += 1
        await state.update_data(cart=cart)
        await callback.message.edit_text(format_cart_text(cart), reply_markup=cart_kb(cart), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("cart_minus:"))
async def cb_cart_minus(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    cart: list[dict] = data.get("cart", [])
    if idx < len(cart):
        cart[idx]["qty"] -= 1
        if cart[idx]["qty"] <= 0:
            cart.pop(idx)
        await state.update_data(cart=cart)
        if cart:
            await callback.message.edit_text(format_cart_text(cart), reply_markup=cart_kb(cart), parse_mode="HTML")
        else:
            await callback.message.edit_text("🛒 Корзина пуста.", parse_mode="HTML")
            await state.set_state(OrderState.main_menu)
    await callback.answer()


@router.callback_query(F.data.startswith("cart_del:"))
async def cb_cart_del(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    cart: list[dict] = data.get("cart", [])
    if idx < len(cart):
        removed = cart.pop(idx)
        await state.update_data(cart=cart)
        if cart:
            await callback.message.edit_text(format_cart_text(cart), reply_markup=cart_kb(cart), parse_mode="HTML")
        else:
            await callback.message.edit_text("🛒 Корзина пуста.", parse_mode="HTML")
            await state.set_state(OrderState.main_menu)
        await callback.answer(f"🗑 {removed['name']} удалён")
        return
    await callback.answer()


@router.callback_query(F.data == "cart_clear")
async def cb_cart_clear(callback: CallbackQuery, state: FSMContext):
    await state.update_data(cart=[])
    await callback.message.edit_text("🗑 Корзина очищена.", parse_mode="HTML")
    await state.set_state(OrderState.main_menu)
    await callback.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()


# ── Оформление заказа ──

@router.callback_query(F.data == "checkout")
async def cb_checkout(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", [])
    if not cart:
        await callback.answer("Корзина пуста!", show_alert=True)
        return
    await callback.message.answer(
        "📝 <b>Оформление заказа</b>\n\nВведите ваше имя:",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )
    await state.set_state(OrderState.checkout_name)
    await callback.answer()


@router.message(OrderState.checkout_name)
async def process_name(message: Message, state: FSMContext):
    if len(message.text.strip()) < 2:
        await message.answer("❌ Введите корректное имя (минимум 2 символа).")
        return
    await state.update_data(name=message.text.strip())
    await message.answer("📱 Введите номер телефона:", parse_mode="HTML")
    await state.set_state(OrderState.checkout_phone)


@router.message(OrderState.checkout_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    # Простая проверка: длина и допустимые символы
    cleaned = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if len(cleaned) < 10 or not cleaned.lstrip("+").isdigit():
        await message.answer("❌ Введите корректный номер телефона (например, +7 777 123 4567).")
        return
    await state.update_data(phone=phone)
    await message.answer(
        "🚗 Выберите способ получения:",
        reply_markup=delivery_type_kb(),
        parse_mode="HTML",
    )
    await state.set_state(OrderState.checkout_type)


@router.callback_query(OrderState.checkout_type, F.data.startswith("dtype:"))
async def process_delivery_type(callback: CallbackQuery, state: FSMContext):
    dtype = callback.data.split(":")[1]
    await state.update_data(delivery_type=dtype)

    if dtype == "delivery":
        await callback.message.answer(
            "📍 Введите адрес доставки (г. Алматы):",
            parse_mode="HTML",
        )
        await state.set_state(OrderState.checkout_address)
    else:
        await state.update_data(address=None)
        await show_order_confirmation(callback.message, state)
    await callback.answer()


@router.message(OrderState.checkout_address)
async def process_address(message: Message, state: FSMContext):
    if len(message.text.strip()) < 5:
        await message.answer("❌ Введите более подробный адрес.")
        return
    await state.update_data(address=message.text.strip())
    await show_order_confirmation(message, state)


async def show_order_confirmation(message: Message, state: FSMContext):
    """Показать сводку заказа перед подтверждением."""
    data = await state.get_data()
    cart = data["cart"]
    total = sum(e["price"] * e["qty"] for e in cart)

    items_lines = "\n".join(
        f"  • {e['name']} × {e['qty']} = {e['price'] * e['qty']}₸"
        for e in cart
    )
    dtype = "🚗 Доставка" if data.get("delivery_type") == "delivery" else "🏪 Самовывоз"
    address_line = f"\n📍 Адрес: {data['address']}" if data.get("address") else ""

    text = (
        f"📋 <b>Подтверждение заказа</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 {data['name']}\n"
        f"📱 {data['phone']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{items_lines}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>Итого: {total}₸</b>\n"
        f"{dtype}{address_line}\n\n"
        f"Всё верно?"
    )
    await message.answer(text, reply_markup=confirm_kb(), parse_mode="HTML")
    await state.set_state(OrderState.confirm)


@router.callback_query(OrderState.confirm, F.data == "order_confirm")
async def cb_order_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    global order_counter
    order_counter += 1
    order_num = order_counter

    data = await state.get_data()
    cart = data["cart"]
    total = sum(e["price"] * e["qty"] for e in cart)
    user = callback.from_user

    # Уведомление админу
    admin_text = format_order_for_admin(data, order_num, user.id, user.username)
    try:
        await bot.send_message(ADMIN_CHAT_ID, admin_text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление админу: {e}")

    # Подтверждение клиенту
    await callback.message.edit_text(
        f"✅ <b>Заказ #{order_num} принят!</b>\n\n"
        f"💰 Сумма: {total}₸\n"
        f"⏱ Примерное время: 30-45 мин.\n\n"
        f"Спасибо за заказ в кафе <b>«{CAFE_NAME}»</b>! 🙏",
        parse_mode="HTML",
    )

    # Сброс состояния
    await state.clear()
    await state.update_data(cart=[])
    await callback.message.answer("Вернуться в меню 👇", reply_markup=main_menu_kb())
    await state.set_state(OrderState.main_menu)
    await callback.answer("Заказ оформлен! ✅")


@router.callback_query(OrderState.confirm, F.data == "order_cancel")
async def cb_order_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Заказ отменён. Ваша корзина сохранена.")
    await callback.message.answer("Вернуться в меню 👇", reply_markup=main_menu_kb())
    await state.set_state(OrderState.main_menu)
    await callback.answer()


# ──────────────────────────────────────────────
# Запуск бота
# ──────────────────────────────────────────────

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    logging.info(f"Бот кафе «{CAFE_NAME}» запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
