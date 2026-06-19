# AI-визитка кафе «Шафран»

Telegram-бот `@shafvizitka_bot` отвечает на вопросы гостей через Gemini 3.5 Flash,
помогает собрать данные для бронирования и пересылает обращения администратору.
При временной перегрузке основной модели используется Gemini 3.1 Flash-Lite.

## Возможности

- ответы на основе `system-prompt.md`;
- история разговора для каждого пользователя;
- передача броней, жалоб и нестандартных вопросов администратору;
- кнопки главного сайта, QR-меню, заказа и отзывов;
- команды `/start`, `/links` и `/reset`;
- понятный резервный ответ при ошибке Gemini.

## Запуск

```bash
python -m venv venv
venv\Scripts\activate
pip install -r task2-whatsapp-bot/requirements.txt
python task2-whatsapp-bot/bot.py
```

Реальные ключи загружаются из корневого `private_config.py`. Если файла нет,
скопируйте `private_config.example.py` как `private_config.py` и заполните значения.

Бот использует polling, поэтому `bot.py` должен постоянно работать на компьютере
или сервере. Cloudflare Workers размещает HTML-сайт, но не запускает этот Python-процесс.
