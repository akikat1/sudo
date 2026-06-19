# review_bot.py — Telegram-бот для сбора отзывов кафе «Шафран», г. Алматы
# python-telegram-bot 21.10 | Python 3.10+

import sys
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# ──────────────────────────────────────────────
# Константы
# ──────────────────────────────────────────────

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

try:
    from private_config import REVIEW_BOT_TOKEN
except ImportError as error:
    raise RuntimeError(
        "Не найден private_config.py. Скопируйте private_config.example.py "
        "как private_config.py и заполните ключи."
    ) from error

BOT_TOKEN = REVIEW_BOT_TOKEN

VENUE_NAME = "Шафран"
CITY = "Алматы"
PHONE = "+7 706 400-86-92"
SITE_URL = "https://sudo.akikating123.workers.dev/"
QR_MENU_URL = "https://sudo.akikating123.workers.dev/qr_menu.html"

REVIEW_LINK_2GIS = "https://go.2gis.com/shafran-almaty"
REVIEW_LINK_GOOGLE = "https://g.page/r/shafran-almaty/review"

DELAY_HOURS = 0.01  # через сколько часов отправить просьбу об отзыве

# Текст приветствия при /start
WELCOME_TEXT = (
    f"Добро пожаловать в «{VENUE_NAME}»! 🧡\n\n"
    f"Мы рады, что вы заглянули к нам в {CITY}.\n"
    "Выберите, что хотите сделать:"
)

# Текст подтверждения после нажатия «Я сделал заказ»
CONFIRMATION_TEXT = "Спасибо! Мы пришлём сообщение чуть позже 😊"

# Текст просьбы об отзыве (отправляется через DELAY_HOURS)
REVIEW_REQUEST_TEXT = (
    f"Привет! Надеемся, что визит в «{VENUE_NAME}» оставил приятные впечатления 🤗\n\n"
    "Будем очень благодарны, если вы поделитесь коротким отзывом — "
    "это поможет нам стать лучше и порадует нашу команду. 💛\n\n"
    "Выберите удобную площадку:"
)

# Текст для кнопки «Связаться с нами»
CONTACT_TEXT = (
    f"📞 Связаться с «{VENUE_NAME}»:\n\n"
    f"📍 Город: {CITY}\n"
    "📍 Адрес: ул. Панфилова, 78\n"
    f"📱 Телефон: {PHONE}\n"
    "📩 Instagram: @shafran_almaty\n\n"
    "Мы всегда на связи!"
)

# Хранилище (in-memory) — chat_id → статус
user_data: dict[int, str] = {}

# ──────────────────────────────────────────────
# Обработчики
# ──────────────────────────────────────────────


def website_links_keyboard() -> InlineKeyboardMarkup:
    """Кнопки для перехода на сайт кафе и в QR-меню."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🏠 Главный сайт", url=SITE_URL),
                InlineKeyboardButton("📱 QR-меню", url=QR_MENU_URL),
            ]
        ]
    )


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Приветственное сообщение с действиями и ссылками на сайт."""
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Я сделал заказ / посетил заведение",
                    callback_data="visited",
                )
            ],
            [
                InlineKeyboardButton(
                    "📞 Связаться с нами",
                    callback_data="contact",
                )
            ],
            [
                InlineKeyboardButton("🏠 Главный сайт", url=SITE_URL),
                InlineKeyboardButton("📱 QR-меню", url=QR_MENU_URL),
            ],
        ]
    )
    await update.message.reply_text(WELCOME_TEXT, reply_markup=keyboard)


async def links_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /links — быстрый переход к сайту и меню."""
    await update.message.reply_text(
        "Выберите, что открыть:",
        reply_markup=website_links_keyboard(),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка нажатий на inline-кнопки."""
    query = update.callback_query
    await query.answer()

    if query.data == "visited":
        chat_id = query.message.chat_id
        user_data[chat_id] = "waiting_review"

        await query.edit_message_text(
            CONFIRMATION_TEXT,
            reply_markup=website_links_keyboard(),
        )

        # Планируем отправку просьбы об отзыве через DELAY_HOURS
        context.job_queue.run_once(
            send_review_request,
            when=DELAY_HOURS * 3600,
            chat_id=chat_id,
            name=f"review_{chat_id}",
        )

    elif query.data == "contact":
        await query.edit_message_text(
            CONTACT_TEXT,
            reply_markup=website_links_keyboard(),
        )


async def send_review_request(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отложенная отправка просьбы оставить отзыв."""
    chat_id = context.job.chat_id

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📍 Отзыв на 2ГИС", url=REVIEW_LINK_2GIS),
                InlineKeyboardButton("🗺 Отзыв на Google", url=REVIEW_LINK_GOOGLE),
            ],
            [
                InlineKeyboardButton("🏠 Главный сайт", url=SITE_URL),
                InlineKeyboardButton("📱 QR-меню", url=QR_MENU_URL),
            ],
        ]
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=REVIEW_REQUEST_TEXT,
        reply_markup=keyboard,
    )

    user_data.pop(chat_id, None)


# ──────────────────────────────────────────────
# Запуск
# ──────────────────────────────────────────────


def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("links", links_handler))
    app.add_handler(CallbackQueryHandler(button_handler))

    print(f"Бот «{VENUE_NAME}» запущен ✅")
    app.run_polling()


if __name__ == "__main__":
    main()
