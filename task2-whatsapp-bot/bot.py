"""
Telegram AI-ассистент кафе «Шафран».

Использует Gemini для ответов гостям и пересылает администратору обращения,
для которых системный промпт возвращает handoff_to_admin needed="true".
"""

import asyncio
import logging
import re
import sys
from pathlib import Path

from google import genai
from google.genai import types
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


# ──────────────────────────────────────────────
# Конфигурация
# ──────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

try:
    from private_config import (
        ADMIN_CHAT_ID,
        ASSISTANT_BOT_TOKEN,
        GEMINI_API_KEY,
    )
except ImportError as error:
    raise RuntimeError(
        "Не найден private_config.py. Скопируйте private_config.example.py "
        "как private_config.py и заполните ключи."
    ) from error

BOT_TOKEN = ASSISTANT_BOT_TOKEN
GEMINI_MODEL = "gemini-3.5-flash"
GEMINI_FALLBACK_MODEL = "gemini-3.1-flash-lite"

SITE_URL = "https://sudo.akikating123.workers.dev/"
QR_MENU_URL = "https://sudo.akikating123.workers.dev/qr_menu.html"
ORDER_BOT_URL = "https://t.me/shafzakaz_bot?start=assistant"
REVIEW_BOT_URL = "https://t.me/shafotziv_bot?start=assistant"
PHONE = "+7 706 400-86-92"

SYSTEM_PROMPT = (BASE_DIR / "system-prompt.md").read_text(encoding="utf-8")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)


# ──────────────────────────────────────────────
# Клавиатуры и утилиты
# ──────────────────────────────────────────────

def links_keyboard() -> InlineKeyboardMarkup:
    """Главный сайт и QR-меню — обратная связь бота с сайтом."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🏠 Главный сайт", url=SITE_URL),
                InlineKeyboardButton("📱 QR-меню", url=QR_MENU_URL),
            ],
            [
                InlineKeyboardButton("🛍️ Заказать", url=ORDER_BOT_URL),
                InlineKeyboardButton("⭐ Оставить отзыв", url=REVIEW_BOT_URL),
            ],
        ]
    )


def build_dialogue(history: list[dict[str, str]], user_text: str) -> str:
    """Передаёт модели компактную историю текущего разговора."""
    lines = [
        "Ниже история текущего Telegram-диалога. "
        "Продолжи разговор, учитывая предыдущие сообщения, и строго соблюдай output_format.",
        "",
    ]
    for item in history[-12:]:
        speaker = "Гость" if item["role"] == "user" else "Ассистент"
        lines.append(f"{speaker}: {item['text']}")
    lines.append(f"Гость: {user_text}")
    lines.extend(
        [
            "",
            "Верни только блок <reply_to_customer> и блок "
            '<handoff_to_admin needed="true или false">, как указано в system prompt.',
        ]
    )
    return "\n".join(lines)


def parse_model_response(text: str) -> tuple[str, bool, str]:
    """Извлекает клиентский ответ и служебный handoff из XML-подобного формата."""
    reply_match = re.search(
        r"<reply_to_customer>\s*(.*?)\s*</reply_to_customer>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    handoff_match = re.search(
        r'<handoff_to_admin\s+needed=["\']?(true|false)["\']?>\s*(.*?)\s*</handoff_to_admin>',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if reply_match:
        reply = reply_match.group(1).strip()
    else:
        reply = re.sub(r"</?[^>]+>", "", text).strip()

    handoff_needed = bool(
        handoff_match and handoff_match.group(1).lower() == "true"
    )
    handoff_text = handoff_match.group(2).strip() if handoff_match else ""

    if not reply:
        reply = (
            f"Не получилось подготовить ответ. Позвоните нам по номеру {PHONE} "
            "или воспользуйтесь кнопками ниже."
        )

    return reply, handoff_needed, handoff_text


async def generate_answer(history: list[dict[str, str]], user_text: str) -> str:
    """Вызывает синхронный Gemini SDK без блокировки Telegram event loop."""
    contents = build_dialogue(history, user_text)

    def request() -> str:
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.35,
            max_output_tokens=1200,
        )
        try:
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=config,
            )
            return response.text or ""
        except Exception as primary_error:
            logging.warning(
                "Gemini %s временно недоступен, пробуем %s: %s",
                GEMINI_MODEL,
                GEMINI_FALLBACK_MODEL,
                primary_error,
            )
            response = gemini_client.models.generate_content(
                model=GEMINI_FALLBACK_MODEL,
                contents=contents,
                config=config,
            )
            return response.text or ""

    return await asyncio.to_thread(request)


async def notify_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    handoff_text: str,
    original_message: str,
) -> None:
    """Отправляет администратору сводку и данные Telegram-пользователя."""
    user = update.effective_user
    username = f"@{user.username}" if user and user.username else "не указан"
    name = user.full_name if user else "не указано"
    user_id = user.id if user else "не указан"
    summary = handoff_text or "Модель запросила передачу диалога администратору."

    text = (
        "🔔 Обращение из AI-бота «Шафран»\n\n"
        f"Гость: {name}\n"
        f"Username: {username}\n"
        f"Telegram ID: {user_id}\n\n"
        f"Сводка:\n{summary}\n\n"
        f"Последнее сообщение гостя:\n{original_message}"
    )
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=text[:4096])


# ──────────────────────────────────────────────
# Telegram handlers
# ──────────────────────────────────────────────

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Приветствует гостя и очищает старую историю разговора."""
    context.user_data["history"] = []
    await update.message.reply_text(
        "Здравствуйте! Я Шафранчик, виртуальный ассистент кафе «Шафран» 🌿\n\n"
        "Могу подсказать адрес и режим работы, рассказать о меню или помочь "
        "передать заявку на бронирование. Чем помочь?",
        reply_markup=links_keyboard(),
    )


async def links_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает сайт, QR-меню и другие Telegram-боты кафе."""
    await update.message.reply_text(
        "Все полезные ссылки кафе «Шафран»:",
        reply_markup=links_keyboard(),
    )


async def reset_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начинает новый диалог без предыдущего контекста."""
    context.user_data["history"] = []
    await update.message.reply_text(
        "История диалога очищена. Можем начать заново 🙂",
        reply_markup=links_keyboard(),
    )


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отвечает через Gemini и при необходимости передаёт обращение админу."""
    if not update.message or not update.message.text:
        return

    user_text = update.message.text.strip()
    if not user_text:
        return

    history: list[dict[str, str]] = context.user_data.setdefault("history", [])
    await update.effective_chat.send_action(ChatAction.TYPING)

    try:
        raw_response = await generate_answer(history, user_text)
        reply, handoff_needed, handoff_text = parse_model_response(raw_response)

        history.append({"role": "user", "text": user_text})
        history.append({"role": "assistant", "text": reply})
        context.user_data["history"] = history[-24:]

        await update.message.reply_text(
            reply[:4096],
            reply_markup=links_keyboard(),
        )

        if handoff_needed:
            try:
                await notify_admin(
                    update,
                    context,
                    handoff_text=handoff_text,
                    original_message=user_text,
                )
            except Exception:
                logging.exception("Не удалось отправить handoff администратору")

    except Exception:
        logging.exception("Ошибка при обращении к Gemini")
        await update.message.reply_text(
            "Сейчас не получилось связаться с AI-ассистентом. "
            f"Позвоните нам по номеру {PHONE} или воспользуйтесь кнопками ниже.",
            reply_markup=links_keyboard(),
        )


async def unsupported_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Подсказывает, что текущая версия работает с текстовыми сообщениями."""
    await update.message.reply_text(
        "Пока я лучше всего понимаю текстовые сообщения. "
        "Напишите вопрос текстом — и я помогу.",
        reply_markup=links_keyboard(),
    )


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    logging.exception("Необработанная ошибка Telegram-бота", exc_info=context.error)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("links", links_handler))
    app.add_handler(CommandHandler("reset", reset_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(~filters.TEXT & ~filters.COMMAND, unsupported_handler))
    app.add_error_handler(error_handler)

    print("AI-бот «Шафранчик» запущен ✅")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
