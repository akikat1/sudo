# 📖 Руководство по настройке бота отзывов — «Шафран»

## 1. Создание бота через @BotFather

1. Откройте Telegram и найдите **@BotFather**.
2. Отправьте команду `/newbot`, укажите имя бота (например, `Шафран Отзывы`) и username (например, `shafotziv_bot`).
3. BotFather пришлёт **токен** вида `123456789:ABCdefGHIjklMNOpqrsTUVwxyz` — сохраните его.

---

## 2. Установка Python и зависимостей

### Установка Python

- **Windows**: скачайте Python 3.10+ с [python.org](https://www.python.org/downloads/) и установите, отметив галочку **Add to PATH**.
- **Linux (Ubuntu/Debian)**:
  ```bash
  sudo apt update && sudo apt install python3 python3-pip python3-venv -y
  ```

### Установка зависимостей

```bash
cd task5-review-bot
pip install -r requirements.txt
```

> Рекомендуется использовать виртуальное окружение:
> ```bash
> python -m venv venv
> source venv/bin/activate   # Linux/macOS
> venv\Scripts\activate      # Windows
> pip install -r requirements.txt
> ```

---

## 3. Где вставить токен

В корне проекта скопируйте `private_config.example.py` как
`private_config.py` и вставьте токен в переменную:

```python
REVIEW_BOT_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
```

`private_config.py` уже добавлен в `.gitignore` и не публикуется в GitHub.

---

## 4. Запуск бота

```bash
python review_bot.py
```

Вы увидите сообщение:

```
Бот «Шафран» запущен ✅
```

Откройте Telegram, найдите вашего бота и отправьте `/start`.

---

## 5. Запуск на постоянной основе (Linux VPS)

### Вариант 1 — screen

```bash
screen -S review_bot
cd /path/to/task5-review-bot
source venv/bin/activate
python review_bot.py
```

Отключение от сессии: `Ctrl+A`, затем `D`.  
Возврат: `screen -r review_bot`.

### Вариант 2 — nohup

```bash
cd /path/to/task5-review-bot
source venv/bin/activate
nohup python review_bot.py > bot.log 2>&1 &
```

Просмотр логов: `tail -f bot.log`.

### Вариант 3 — systemd (рекомендуется)

Создайте файл `/etc/systemd/system/review-bot.service`:

```ini
[Unit]
Description=Telegram Review Bot — Шафран
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/task5-review-bot
ExecStart=/path/to/task5-review-bot/venv/bin/python review_bot.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable review-bot
sudo systemctl start review-bot
sudo systemctl status review-bot
```

---

## 6. Тексты сообщений (готовые для копирования)

### Приветствие (`/start`)

```
Добро пожаловать в «Шафран»! 🧡

Мы рады, что вы заглянули к нам в Алматы.
Выберите, что хотите сделать:
```

### Подтверждение посещения

```
Спасибо! Мы пришлём сообщение чуть позже 😊
```

### Просьба об отзыве (через 2 часа)

```
Привет! Надеемся, что визит в «Шафран» оставил приятные впечатления 🤗

Будем очень благодарны, если вы поделитесь коротким отзывом — это поможет нам стать лучше и порадует нашу команду. 💛

Выберите удобную площадку:
```

### Контактная информация

```
📞 Связаться с «Шафран»:

📍 Город: Алматы
📍 Адрес: ул. Панфилова, 78
📱 Телефон: +7 706 400-86-92
📩 Instagram: @shafran_almaty

Мы всегда на связи!
```

---

## 7. Как изменить тексты

Все тексты хранятся в **константах** в начале файла `review_bot.py`:

| Константа             | Что содержит                          |
|-----------------------|---------------------------------------|
| `VENUE_NAME`          | Название кафе                         |
| `CITY`                | Город                                 |
| `WELCOME_TEXT`        | Приветственное сообщение              |
| `CONFIRMATION_TEXT`   | Ответ после нажатия «Я посетил»       |
| `REVIEW_REQUEST_TEXT` | Текст просьбы об отзыве               |
| `CONTACT_TEXT`        | Контактная информация                 |
| `REVIEW_LINK_2GIS`   | Ссылка на отзыв в 2ГИС               |
| `REVIEW_LINK_GOOGLE`  | Ссылка на отзыв в Google Maps         |
| `DELAY_HOURS`         | Задержка перед отправкой (в часах)    |

Просто измените значение нужной константы и перезапустите бота.

---

## ❓ FAQ

**Бот не отвечает после запуска?**  
Проверьте, что токен вставлен правильно и нет опечаток.

**Сообщение об отзыве не приходит?**  
Оно отправляется через 2 часа. Для теста измените `DELAY_HOURS = 2` на `DELAY_HOURS = 0.01` (≈ 36 секунд).

**Можно ли добавить ещё площадки для отзывов?**  
Да — добавьте ещё одну `InlineKeyboardButton` с `url=` в функции `send_review_request`.
