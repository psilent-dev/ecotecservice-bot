"""Все пользовательские тексты бота «Экотек Сервис».

Формальное обращение на «вы». Стиль — премиум и живой, без панибратства.
Разделитель блоков: ━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Старт и телефон
# ---------------------------------------------------------------------------

START_GREETING = (
    "🔧 <b>Добро пожаловать в {service_name}!</b>\n\n"
    "Мы — команда, которая вернёт вашему авто уверенность на дороге 🚗💨\n\n"
    "━━━━━━━━━━━━━━━━\n"
    "📝 Оставить заявку\n"
    "💰 Узнать стоимость\n"
    "❓ Задать вопрос мастеру\n"
    "🎁 Получить скидку за друга\n"
    "━━━━━━━━━━━━━━━━\n\n"
    "Выберите, что вам нужно 👇"
)

SHARE_PHONE_REQUEST = (
    "📱 <b>Давайте познакомимся!</b>\n\n"
    "Отправьте свой номер телефона — так мастер сможет "
    "быстро с вами связаться 🤝\n\n"
    "Нажмите кнопку ниже 👇"
)

PHONE_RECEIVED = (
    "✅ <b>Отлично, номер сохранён!</b>\n\n"
    "Теперь вы можете оставить заявку в один клик 🚀"
)

ERROR_PHONE_INVALID = (
    "⚠️ <b>Не получилось распознать номер</b>\n\n"
    "Нажмите кнопку ниже или введите телефон в формате "
    "<code>+7XXXXXXXXXX</code> 📱"
)

BTN_SHARE_PHONE = "📱 Отправить телефон"

# ---------------------------------------------------------------------------
# Главное меню и кнопки
# ---------------------------------------------------------------------------

MENU_MAIN = (
    "👇 <b>Главное меню</b>\n\n"
    "Выберите, что вам нужно — мы на связи 🚗"
)

MENU_BUTTONS = {
    "booking": "📝 Записаться",
    "price": "💰 Узнать цену",
    "question": "❓ Задать вопрос",
    "profile": "👤 Мой профиль",
    "bonuses": "🎁 Бонусы",
    "contacts": "📍 Контакты",
    "cancel": "❌ Отмена",
    "back": "↩️ Назад",
    "admin_requests": "📥 Заявки",
    "admin_answered": "💬 Отвеченные",
    "admin_clients": "👥 Клиенты",
    "admin_broadcast": "📢 Рассылка",
    "admin_services": "🔧 Услуги",
    "admin_promo": "🎁 Промо",
    "admin_admins": "👤 Админы",
    "admin_settings": "⚙️ Настройки",
    "admin_exit": "↩️ В меню клиента",
}

BTN_BACK = MENU_BUTTONS["back"]
BTN_CANCEL = MENU_BUTTONS["cancel"]
BTN_CONFIRM = "✅ Подтвердить"
BTN_SKIP = "⏭ Пропустить"
BTN_MAIN_MENU = "🏠 Меню"
BTN_PAGE_PREV = "⬅️"
BTN_PAGE_NEXT = "➡️"
BTN_ADD = "➕ Добавить"
BTN_EDIT = "✏️ Изменить"
BTN_TOGGLE = "🔄 Скрыть/Показать"
BTN_DELETE = "🗑 Удалить"
BTN_REPLY = "💬 Ответить"
BTN_REPLY_AGAIN = "💬 Ответить ещё"
BTN_CLOSE = "🔒 Закрыть"
BTN_REOPEN = "↩️ Вернуть в работу"
BTN_WRITE = "✍️ Написать"
BTN_GIFT = "🎁 Бонус"
BTN_BLOCK = "🚫 Заблокировать"
BTN_UNBLOCK = "✅ Разблокировать"
BTN_SEARCH = "🔎 Поиск"
BTN_ADD_ADMIN = "➕ Назначить админа"
BTN_ACCEPT_ON = "🔔 Приём заявок: да"
BTN_ACCEPT_OFF = "🔕 Приём заявок: нет"

FSM_CANCELLED = (
    "↩️ <b>Ок, отменили</b>\n\n"
    "Вы снова в меню — выбирайте следующий шаг 👇"
)
USER_BLOCKED = (
    "🚫 <b>Доступ к боту ограничен</b>\n\n"
    "Свяжитесь с сервисом по телефону <code>{phone}</code> 📞"
)

ADMIN_MENU_BUTTONS = {
    "requests": MENU_BUTTONS["admin_requests"],
    "clients": MENU_BUTTONS["admin_clients"],
    "broadcast": MENU_BUTTONS["admin_broadcast"],
    "services": MENU_BUTTONS["admin_services"],
    "promos": MENU_BUTTONS["admin_promo"],
    "admins": MENU_BUTTONS["admin_admins"],
    "settings": MENU_BUTTONS["admin_settings"],
}

# ---------------------------------------------------------------------------
# Запись (FSM)
# ---------------------------------------------------------------------------

BOOKING_CHOOSE_SERVICE = (
    "🛠 <b>Шаг 1 из 4 — Что будем делать?</b>\n\n"
    "Выберите категорию услуги 👇"
)

BOOKING_ENTER_PROBLEM = (
    "📝 <b>Шаг 2 из 4 — Опишите проблему</b>\n\n"
    "Расскажите своими словами, что беспокоит: стуки, скрипы, "
    "ошибки на панели, странное поведение 🚨\n\n"
    "Чем подробнее — тем точнее мастер подготовится 👌"
)
BOOKING_COMMENT = BOOKING_ENTER_PROBLEM

BOOKING_ENTER_CAR = (
    "🚗 <b>Шаг 3 из 4 — Ваш автомобиль</b>\n\n"
    "Напишите одной строкой: марку, модель и госномер.\n\n"
    "Пример: <code>Toyota Camry, А123БВ777</code>"
)
BOOKING_CAR_INFO = BOOKING_ENTER_CAR

BOOKING_CONFIRM = (
    "📋 <b>Шаг 4 из 4 — Проверьте заявку</b>\n\n"
    "🛠 Услуга: <b>{service}</b>\n"
    "🚗 Авто: <b>{car}</b>\n"
    "📝 Описание: {problem}\n"
    "{discounts}\n"
    "━━━━━━━━━━━━━━━━\n"
    "Всё верно? Отправляем мастеру? 👇"
)

BOOKING_CREATED = (
    "🎉 <b>Заявка №{request_id} принята!</b>\n\n"
    "Мастер уже получил уведомление и свяжется с вами "
    "в ближайшее время ⏱\n\n"
    "А пока можете посмотреть наш профиль или задать вопрос 👇"
)

BOOKING_CANCELLED = (
    "↩️ <b>Запись отменена</b>\n\n"
    "Ничего страшного — можно начать заново из меню 👇"
)
BOOKING_INVALID_SERVICE = (
    "⚠️ Выберите категорию из кнопок ниже — так заявка дойдёт правильно 🛠"
)
BOOKING_EMPTY_TEXT = (
    "✍️ Напишите пару предложений текстом — мастеру важно понять задачу 📝"
)

# ---------------------------------------------------------------------------
# Узнать цену
# ---------------------------------------------------------------------------

PRICE_CHOOSE_SERVICE = (
    "💰 <b>Узнаем стоимость</b>\n\n"
    "Выберите услугу — мастер посчитает цену "
    "и вернётся с ответом 👇"
)

PRICE_CAR_INFO = (
    "🚗 <b>Автомобиль для расчёта</b>\n\n"
    "Напишите марку, модель и год — так оценка будет точнее 👌\n\n"
    "Пример: <code>Toyota Camry 2018</code>"
)
PRICE_DETAILS = (
    "📝 <b>Какие работы интересуют?</b>\n\n"
    "Опишите коротко, что нужно сделать — мастер сориентирует по цене 💰"
)

PRICE_CONFIRM = (
    "💵 <b>Проверьте запрос</b>\n\n"
    "🛠 Услуга: <b>{service}</b>\n"
    "🚗 Авто: <b>{car}</b>\n\n"
    "Отправляем мастеру? 👇"
)

PRICE_CREATED = (
    "✅ <b>Запрос №{request_id} отправлен!</b>\n\n"
    "Мастер посчитает стоимость и вернётся с ответом 💬"
)

PRICE_LIST_EMPTY = (
    "📭 В этой категории пока нет активных услуг.\n\n"
    "Выберите другую или напишите мастеру напрямую ❓"
)
PRICE_SERVICE_ITEM = "• <b>{name}</b>\n{description}\n💰 {price}"
PRICE_FROM = "от {price_from} ₽"
PRICE_RANGE = "от {price_from} ₽ до {price_to} ₽"
PRICE_ON_REQUEST = "по запросу"
PRICE_CANCELLED = (
    "↩️ <b>Запрос стоимости отменён</b>\n\n"
    "Можно вернуться к нему в любой момент 💰"
)

# ---------------------------------------------------------------------------
# Вопрос мастеру
# ---------------------------------------------------------------------------

QUESTION_ENTER_TEXT = (
    "❓ <b>Задайте свой вопрос</b>\n\n"
    "Напишите всё, что вас интересует: по ремонту, "
    "запчастям, срокам, гарантии 🛠\n\n"
    "Мастер ответит лично 💬"
)
QUESTION_PROMPT = QUESTION_ENTER_TEXT

QUESTION_CONFIRM = (
    "📨 <b>Проверьте вопрос</b>\n\n"
    "{text}\n\n"
    "━━━━━━━━━━━━━━━━\n"
    "Отправляем мастеру? 👇"
)

QUESTION_CREATED = (
    "📨 <b>Вопрос №{request_id} отправлен!</b>\n\n"
    "Мастер ответит вам в ближайшее время ⏱"
)

QUESTION_CANCELLED = (
    "↩️ <b>Вопрос не отправлен</b>\n\n"
    "Если передумаете — кнопка всегда на месте ❓"
)
QUESTION_EMPTY = "✍️ Напишите вопрос текстом — так мастеру будет проще ответить 💬"

# ---------------------------------------------------------------------------
# Профиль и бонусы
# ---------------------------------------------------------------------------

PROFILE_TEXT = (
    "👤 <b>Ваш профиль</b>\n\n"
    "🪪 Имя: <b>{full_name}</b>\n"
    "📱 Телефон: <b>{phone}</b>\n"
    "🚗 Визитов: <b>{visits}</b>\n"
    "👥 Приглашено друзей: <b>{refs}</b>\n\n"
    "━━━━━━━━━━━━━━━━\n"
    "🎁 <b>Ваши бонусы:</b>\n"
    "{bonuses}\n"
    "━━━━━━━━━━━━━━━━\n\n"
    "🔗 <b>Ваша реферальная ссылка:</b>\n"
    "<code>{ref_link}</code>\n\n"
    "Поделитесь с другом — он получит <b>скидку 10%</b>, "
    "а вы — <b>бесплатную диагностику</b> 🎁"
)

PROFILE_NO_PHONE = "не указан"
PROFILE_REQUESTS_HEADER = "📋 <b>Ваши последние заявки</b>"
PROFILE_REQUEST_ITEM = "№{id} · {type} · {status} · {created_at}"
PROFILE_NO_REQUESTS = "📭 Заявок пока нет — самое время оставить первую 🚀"

BONUS_EMPTY = "• Пока пусто. Пригласите друга и получите подарок 🎁"
BONUS_LOYALTY_2ND = "• 🎉 <b>Скидка 10% на 2-й визит</b>"
BONUS_REFERRAL_10 = "• 🎁 <b>Реферальная скидка 10%</b>"
BONUS_FREE_DIAG = "• 🔍 <b>Бесплатная диагностика</b>"

BONUS_DETAILS = (
    "🎁 <b>Ваши бонусы — подробно</b>\n\n"
    "{details}\n\n"
    "━━━━━━━━━━━━━━━━\n"
    "💡 Скидки применяются автоматически при оформлении заявки "
    "и не суммируются между собой."
)

BONUS_DETAIL_LOYALTY = (
    "🎉 <b>Скидка 10% на 2-й визит</b>\n"
    "Вы получаете её после первого визита. Применится "
    "автоматически на следующей заявке."
)

BONUS_DETAIL_REFERRAL = (
    "🎁 <b>Реферальная скидка 10%</b>\n"
    "Вы пришли по ссылке друга. Скидка сгорит при первой же заявке."
)

BONUS_DETAIL_FREE_DIAG = (
    "🔍 <b>Бесплатная диагностика</b>\n"
    "Награда за приглашённого друга. Применится автоматически, "
    "когда вы оставите заявку на диагностику."
)

BONUSES_TEXT = BONUS_DETAILS
BONUSES_STATUS_ACTIVE = "активна"
BONUSES_STATUS_INACTIVE = "не активна"
BONUSES_NO_PROMOS = "📭 Сейчас дополнительных акций нет — следите за обновлениями 🎁"
BONUSES_PROMO_ITEM = (
    "🏷 <b>{title}</b>\n"
    "{description}\n"
    "Скидка: <b>{discount}</b>\n"
    "Срок: {valid_until}"
)
BONUSES_PROMO_UNLIMITED = "бессрочно"

# ---------------------------------------------------------------------------
# Контакты
# ---------------------------------------------------------------------------

CONTACTS_TEXT = (
    "📍 <b>{service_name}</b>\n\n"
    "🏠 Адрес: {address}\n"
    "📞 Телефон: <code>{phone}</code>\n"
    "🕒 Режим работы: {hours}\n\n"
    "━━━━━━━━━━━━━━━━\n"
    "Ждём вас! 🚗💨"
)
CONTACTS_MAPS_BUTTON = "🗺 Открыть карту"
CONTACTS_PHONE_BUTTON = "📞 Скопировать телефон"

# ---------------------------------------------------------------------------
# Рефералы и лояльность
# ---------------------------------------------------------------------------

REFERRAL_NOTIFICATION = (
    "🎉 <b>По вашей ссылке пришёл друг!</b>\n\n"
    "Вам начислена <b>бесплатная диагностика</b> 🔍\n"
    "Она применится автоматически при следующей заявке."
)

REFERRAL_WELCOME = (
    "🎁 <b>Вам подарок от друга!</b>\n\n"
    "Вы получили <b>скидку 10%</b> на первую заявку. "
    "Приятно познакомиться 🤝"
)

LOYALTY_2ND_VISIT = BONUS_LOYALTY_2ND
LOYALTY_2ND_VISIT_HINT = BONUS_DETAIL_LOYALTY
LOYALTY_REFERRAL = (
    "👥 <b>Реферальная программа</b>\n"
    "Пригласите друга по своей ссылке: он получит скидку 10% "
    "на первый визит, вы — бесплатную диагностику 🎁"
)
LOYALTY_FREE_DIAGNOSTICS = BONUS_FREE_DIAG
LOYALTY_REFERRAL_APPLIED = REFERRAL_WELCOME
LOYALTY_REFERRAL_SELF = (
    "😅 Свою ссылку использовать нельзя — отправьте её другу 🎁"
)
LOYALTY_REFERRAL_ALREADY = (
    "ℹ️ Реферальный код уже был применён ранее — повторно не сработает 🔗"
)
LOYALTY_REFERRAL_INVALID = (
    "⚠️ Реферальный код не найден. Проверьте ссылку и попробуйте ещё раз 🔗"
)
LOYALTY_INVITER_REWARD = REFERRAL_NOTIFICATION
LOYALTY_DISCOUNT_USED = "🎉 Скидка 10% на второй визит применена."

DISCOUNT_LINE_LOYALTY = "🎉 Учтена скидка 10% на 2-й визит"
DISCOUNT_LINE_REFERRAL = "🎁 Учтена реферальная скидка 10%"
DISCOUNT_LINE_FREE_DIAG = "🔍 Учтена бесплатная диагностика"

# ---------------------------------------------------------------------------
# Категории, типы, статусы
# ---------------------------------------------------------------------------

SERVICE_CATEGORIES = {
    "diagnostics": "🔍 Диагностика",
    "maintenance": "🛠 ТО",
    "suspension": "🔧 Ходовая",
    "electrical": "⚡ Электрика",
    "tires": "🛞 Шиномонтаж",
    "tuning": "🏎 Тюнинг",
    "overhaul": "⚙️ Капремонт",
}

REQUEST_TYPE_LABELS = {
    "booking": "запись",
    "price": "цена",
    "question": "вопрос",
}

REQUEST_STATUS_LABELS = {
    "new": "новая",
    "in_progress": "в работе",
    "answered": "отвечена",
    "closed": "закрыта",
}

# ---------------------------------------------------------------------------
# Админ-панель
# ---------------------------------------------------------------------------

ADMIN_WELCOME = (
    "👑 <b>Добро пожаловать, хозяин!</b>\n\n"
    "Всё под контролем. Выберите раздел 👇"
)
ADMIN_MENU = ADMIN_WELCOME

ADMIN_ACCESS_DENIED = (
    "🚫 <b>Недостаточно прав</b>\n\n"
    "Этот раздел доступен только владельцу сервиса 👑"
)

ADMIN_NEW_REQUEST = (
    "🔔 <b>Новая заявка №{request_id}</b>\n\n"
    "📌 Тип: {type}\n"
    "🛠 Услуга: {service}\n"
    "🚗 Авто: {car}\n"
    "👤 Клиент: {name} (@{username})\n"
    "📱 Телефон: {phone}\n\n"
    "💬 Сообщение:\n<i>{text}</i>\n"
    "{discounts}\n"
    "━━━━━━━━━━━━━━━━"
)

ADMIN_REQUESTS_EMPTY = (
    "📭 <b>Новых заявок нет</b>\n\n"
    "Как только клиент напишет — карточка появится здесь 📥"
)
ADMIN_REQUESTS_HEADER = "📥 <b>Заявки:</b> {count}"

ADMIN_REQUEST_CARD = (
    "🔔 <b>Заявка №{id}</b>\n\n"
    "📌 Тип: {type}\n"
    "📊 Статус: {status}\n"
    "👤 Клиент: {full_name} (id {tg_id})\n"
    "📱 Телефон: {phone}\n"
    "🛠 Услуга: {service}\n"
    "🚗 Авто: {car_info}\n\n"
    "💬 {text}\n"
    "━━━━━━━━━━━━━━━━"
)

ADMIN_REQUEST_NO_SERVICE = "не указана"
ADMIN_REQUEST_NO_CAR = "не указан"
ADMIN_REPLY_PROMPT = (
    "💬 <b>Ответ по заявке №{id}</b>\n\n"
    "Напишите текст — клиент получит его в этот же чат ✍️"
)
ADMIN_REPLY_SENT = "✅ Ответ отправлен клиенту!"
ADMIN_REPLY_TO_CLIENT = (
    "💬 <b>Ответ от мастера</b>\n\n"
    "{reply}\n\n"
    "━━━━━━━━━━━━━━━━\n"
    "Заявка №{id}"
)
ADMIN_STATUS_UPDATED = "📊 Статус заявки №{id}: <b>{status}</b>."
ADMIN_TAKE_IN_PROGRESS = "🛠 Заявка №{id} взята в работу."
ADMIN_REQUEST_CLOSED = "🔒 Заявка №{request_id} закрыта."
ADMIN_REQUEST_NOT_FOUND = "⚠️ Заявка №{id} не найдена."
ADMIN_REPLY_EMPTY = "✍️ Ответ не может быть пустым — напишите пару строк 💬"

ADMIN_BROADCAST_PROMPT = (
    "📢 <b>Рассылка</b>\n\n"
    "Отправьте текст — его получат все клиенты бота ✉️"
)
ADMIN_BROADCAST_CONFIRM = (
    "📢 <b>Предпросмотр рассылки</b>\n\n"
    "━━━━━━━━━━━━━━━━\n"
    "{text}\n"
    "━━━━━━━━━━━━━━━━\n\n"
    "Отправляем всем клиентам? 👇"
)
ADMIN_BROADCAST_DONE = (
    "✅ <b>Рассылка завершена!</b>\n\n"
    "📨 Отправлено: <b>{ok}</b>\n"
    "❌ Ошибок: <b>{fail}</b>"
)
ADMIN_BROADCAST_CANCELLED = "↩️ Рассылка отменена — текст никому не ушёл 📢"
ADMIN_BROADCAST_EMPTY = "✍️ Текст рассылки не может быть пустым 📢"

ADMIN_SERVICES_HEADER = "🔧 <b>Услуги</b>"
ADMIN_SERVICE_ITEM = "{id}. {name} ({category}) · {price} · {active}"
ADMIN_SERVICE_ACTIVE = "активна"
ADMIN_SERVICE_INACTIVE = "скрыта"
ADMIN_SERVICE_CREATED = "✅ Услуга «{name}» добавлена 🔧"
ADMIN_SERVICE_UPDATED = "✅ Услуга «{name}» обновлена 🔧"
ADMIN_SERVICE_DELETED = "🗑 Услуга удалена."
ADMIN_SERVICE_NOT_FOUND = "⚠️ Услуга не найдена."
ADMIN_SERVICE_PROMPT_NAME = "✍️ Введите название услуги 🔧"
ADMIN_SERVICE_PROMPT_CATEGORY = "🛠 <b>Выберите категорию услуги</b> 👇"
ADMIN_SERVICE_PROMPT_DESCRIPTION = (
    "📝 Введите описание услуги или нажмите «Пропустить» ⏭"
)
ADMIN_SERVICE_PROMPT_PRICE_FROM = (
    "💰 Введите цену «от» в рублях (целое число) или 0, если цена по запросу."
)
ADMIN_SERVICE_PROMPT_PRICE_TO = (
    "💰 Введите цену «до» в рублях или 0, если верхней границы нет."
)
ADMIN_SERVICE_INVALID_PRICE = "⚠️ Введите целое неотрицательное число 💰"

ADMIN_PROMO_HEADER = "🎁 <b>Промо-акции</b>"
ADMIN_PROMO_ITEM = "{id}. {title} · {discount} · до {valid_until} · {active}"
ADMIN_PROMO_ACTIVE = "активна"
ADMIN_PROMO_INACTIVE = "скрыта"
ADMIN_PROMO_CREATED = "✅ Акция «{title}» добавлена 🎁"
ADMIN_PROMO_UPDATED = "✅ Акция «{title}» обновлена 🎁"
ADMIN_PROMO_DELETED = "🗑 Акция удалена."
ADMIN_PROMO_NOT_FOUND = "⚠️ Акция не найдена."
ADMIN_PROMO_PROMPT_TITLE = "✍️ Введите название акции 🎁"
ADMIN_PROMO_PROMPT_DESCRIPTION = "📝 Введите описание акции 🎁"
ADMIN_PROMO_PROMPT_DISCOUNT = (
    "💰 Введите размер скидки, например: 10% или бесплатная диагностика."
)
ADMIN_PROMO_PROMPT_VALID_UNTIL = (
    "📅 Введите срок действия в формате ДД.ММ.ГГГГ или нажмите «Пропустить» ⏭"
)
ADMIN_PROMO_INVALID_DATE = "⚠️ Некорректная дата. Используйте формат ДД.ММ.ГГГГ 📅"

ADMIN_ADMINS_HEADER = "👤 <b>Администраторы</b>"
ADMIN_ADMINS_ITEM = "{full_name} · {tg_id} · @{username}"
ADMIN_ADMIN_NO_USERNAME = "без username"
ADMIN_ADMIN_ADD_PROMPT = (
    "🆔 Отправьте Telegram ID пользователя, которого нужно назначить администратором."
)
ADMIN_ADMIN_REMOVE_PROMPT = (
    "🆔 Отправьте Telegram ID администратора, которого нужно снять с роли."
)
ADMIN_ADMIN_ADDED = "✅ Пользователь {tg_id} назначен администратором 👑"
ADMIN_ADMIN_EXISTS = "ℹ️ Пользователь {tg_id} уже является администратором."
ADMIN_ADMIN_NOT_FOUND = (
    "⚠️ Пользователь {tg_id} ещё не запускал бота. Пусть нажмёт /start 🚀"
)
ADMIN_ADMIN_REMOVED = "✅ Пользователь {tg_id} снят с роли администратора."
ADMIN_ADMIN_CANNOT_REMOVE_OWNER = "👑 Владельца нельзя снять с роли администратора."
ADMIN_INVALID_TG_ID = "⚠️ Укажите корректный числовой Telegram ID 🆔"
ADMIN_NEW_ADMIN_GRANTED = (
    "👑 <b>Вам выданы права администратора</b>\n\n"
    "Теперь вы можете управлять заявками, клиентами "
    "и рассылкой в <b>{service_name}</b> 🔧"
)

ADMIN_SETTINGS_TEXT = (
    "⚙️ <b>Настройки сервиса</b>\n\n"
    "🏷 Название: {service_name}\n"
    "📞 Телефон: {phone}\n"
    "🏠 Адрес: {address}\n"
    "🕒 Часы работы: {hours}\n"
    "🌍 Часовой пояс: {tz}\n"
    "🤖 Бот: @{bot_username}"
)

ADMIN_CLIENTS_HEADER = "👥 <b>Клиенты</b> · стр. {page}"
ADMIN_CLIENT_ITEM = "{full_name} · {tg_id} · {phone} · визитов: {visits_count}"
ADMIN_CLIENT_SEARCH_PROMPT = (
    "🔎 Введите имя, телефон, username или Telegram ID 👇"
)
ADMIN_CLIENT_NOT_FOUND = "⚠️ Клиенты по запросу «{query}» не найдены 🔎"
ADMIN_CLIENTS_EMPTY = "📭 Клиентов пока нет — пусть нажмут /start 🚀"
ADMIN_CLIENT_CARD = (
    "👤 <b>Клиент</b>\n\n"
    "🪪 Имя: {full_name}\n"
    "🆔 Telegram ID: {tg_id}\n"
    "🔗 Username: @{username}\n"
    "📱 Телефон: {phone}\n"
    "🚗 Визитов: {visits_count}\n"
    "👥 Рефералов: {referral_count}\n"
    "🎁 Скидка 10%: {discount_10}\n"
    "🔍 Бесплатная диагностика: {free_diagnostics}\n"
    "🎉 Скидка на 2-й визит: {loyalty_2nd}"
)
ADMIN_FLAG_YES = "да"
ADMIN_FLAG_NO = "нет"
ADMIN_VISIT_MARKED = (
    "✅ Визит клиента {full_name} учтён. Всего визитов: {visits_count} 🚗"
)
ADMIN_GIFT_TO_CLIENT = (
    "🎁 <b>Подарок от {service_name}!</b>\n\n"
    "{text}"
)

ADMIN_ESCALATION_30 = (
    "⏰ <b>Напоминание!</b>\n"
    "Заявка №{request_id} без ответа уже 30 минут 🙈"
)
ADMIN_ESCALATION_120 = (
    "🚨 <b>СРОЧНО!</b>\n"
    "Заявка №{request_id} ждёт ответа 2 часа 😱"
)
ESCALATION_30MIN = ADMIN_ESCALATION_30
ESCALATION_2H = ADMIN_ESCALATION_120

INACTIVE_CLIENT_REMINDER = (
    "👋 <b>Давно не виделись!</b>\n\n"
    "Пора заехать на ТО — авто будет вам благодарно 🚗\n\n"
    "Оставьте заявку в пару касаний 👇"
)

ERROR_GLOBAL = (
    "⚠️ <b>Произошла ошибка</b>\n\n"
    "Попробуйте ещё раз или напишите нам чуть позже 🙏"
)
