# 🍽 Telegram-бот заказов — Кафе «Шафран», г. Алматы

Telegram-бот для приёма заказов с корзиной, оформлением доставки/самовывоза и уведомлениями администратору.

## 📋 Возможности

- Каталог блюд по категориям (бургеры, пицца, салаты, напитки, десерты)
- Корзина: добавление, изменение количества (+/−), удаление, очистка
- Оформление заказа: имя → телефон → способ получения → адрес (если доставка)
- Уведомление администратору о новом заказе
- Подтверждение заказа клиенту с номером и суммой
- Цены в тенге (₸)

## 🚀 Быстрый старт

### 1. Получение токена бота

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
2. Отправьте `/newbot`
3. Введите имя бота (например, «Кафе Шафран»)
4. Введите username бота (например, `shafzakaz_bot`)
5. Скопируйте полученный **токен** (формат: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка

Откройте `bot.py` и задайте:

**Токен бота** — один из двух способов:

```python
# Способ 1: переменная окружения (рекомендуется)
# Windows:
set BOT_TOKEN=ваш_токен
# Linux/Mac:
export BOT_TOKEN=ваш_токен

# Способ 2: напрямую в коде (для тестирования)
BOT_TOKEN = "ваш_токен"
```

**ADMIN_CHAT_ID** — ваш Telegram ID для получения уведомлений о заказах:

```python
ADMIN_CHAT_ID = 123456789
```

> 💡 Чтобы узнать свой Telegram ID, отправьте любое сообщение боту [@userinfobot](https://t.me/userinfobot)

### 4. Запуск

```bash
python bot.py
```

## 🏗 Деплой на сервер

### Вариант 1: screen (быстро)

```bash
screen -S orderbot
python bot.py
# Ctrl+A, D — отключиться от сессии
# screen -r orderbot — вернуться
```

### Вариант 2: systemd (надёжно)

Создайте файл `/etc/systemd/system/orderbot.service`:

```ini
[Unit]
Description=Telegram Order Bot — Кафе Шафран
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/task3-order-bot
Environment=BOT_TOKEN=ваш_токен
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable orderbot
sudo systemctl start orderbot
sudo systemctl status orderbot   # проверка
```

## 🛠 Стек

- Python 3.10+
- aiogram 3.13.0
- FSM (конечный автомат) для управления состояниями диалога

## 📁 Структура

```
task3-order-bot/
├── bot.py              # Основной файл бота
├── requirements.txt    # Зависимости
└── README.md           # Документация
```
