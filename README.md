# Экотек Сервис — Telegram-бот автосервиса

Бот принимает записи, запросы цены и вопросы клиентов, уведомляет мастера в Telegram и даёт ответить прямо из чата. Есть прайс, промо, реферальная программа (скидка другу 10% и бесплатная диагностика пригласившему), скидка 10% на второй визит, рассылка и админ-панель.

## Стек

- Python 3.11
- aiogram 3.x
- SQLAlchemy 2.0 (async) + aiosqlite
- APScheduler
- pydantic-settings
- Docker / docker-compose

## Установка локально

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Linux/macOS: cp .env.example .env
```

Заполните `.env`: `BOT_TOKEN`, `ADMIN_CHAT_ID`, `OWNER_ID`, `ADMIN_IDS`, контакты сервиса, `BOT_USERNAME`. Имена `BOT_TOKEN` и `ADMIN_CHAT_ID` совпадают с сайтом Mini App.

```bash
python main.py
```

Если появляется `Cannot connect to host api.telegram.org` — Telegram API недоступен без VPN/прокси. Включите VPN **или** добавьте в `.env`:

```
TELEGRAM_PROXY=socks5://127.0.0.1:1080
```

(порт подставьте из вашего клиента: Clash, Hiddify, v2rayN и т.п.)

База SQLite создаётся в `data/bot.db`, логи — в `logs/bot.log`.

## Запуск через Docker

```bash
copy .env.example .env
# заполните .env
docker-compose up -d
docker-compose logs -f
```

Тома `./data` и `./logs` сохраняют базу и логи на хосте.

## Деплой на VPS

Минимальные требования: **1 CPU, 512 MB RAM, Ubuntu 22.04**.

1. Установите Docker и docker-compose:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER
```

2. Клонируйте проект и создайте `.env` из `.env.example` (токен бота, ваш Telegram ID).

3. Запуск:

```bash
docker-compose up -d
docker-compose logs -f
```

Перезапуск: `docker-compose restart`.

## Как узнать свой Telegram ID

Напишите боту [@userinfobot](https://t.me/userinfobot) — он пришлёт ваш `Id`. Это число нужно в `OWNER_ID` и `ADMIN_IDS`.

## Структура проекта

```
config.py              # настройки из .env
texts.py               # все пользовательские тексты
main.py                # точка входа, polling, логи, error handler
database/              # модели SQLAlchemy и репозитории
handlers/              # клиентские и админ-сценарии
keyboards/             # reply и inline-клавиатуры
states/                # FSM
filters/               # IsAdmin, IsOwner
middlewares/           # сессия БД, антифлуд
services/              # лояльность, уведомления, планировщик
utils/                 # валидаторы, палитра
data/                  # SQLite
logs/                  # bot.log
```

Подробная инструкция для владельца — в `MANUAL.md`.
