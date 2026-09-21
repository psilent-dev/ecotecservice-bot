"""Все пользовательские тексты бота «Экотек Сервис»."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Старт
# ---------------------------------------------------------------------------

START_GREETING = (
    "🚙 <b>Добро пожаловать в «{service_name}»!</b>\n\n"
    "Мы занимаемся профессиональным ремонтом и ТО иномарок в Ростове-на-Дону.\n\n"
    "💎 Вам начислена скидка <b>10%</b> на первый визит "
    "при записи через приложение."
)

USER_BLOCKED = (
    "🚫 <b>Доступ к боту ограничен</b>\n\n"
    "Свяжитесь с диспетчером: <code>{phone}</code>"
)

BTN_SHARE_PHONE = "📱 Отправить мой номер телефона"
ERROR_PHONE_INVALID = (
    "⚠️ Не получилось распознать номер.\n"
    "Нажмите кнопку ниже или введите телефон в формате "
    "<code>+7XXXXXXXXXX</code>."
)
PHONE_NOT_BOUND = "Не привязан"

# ---------------------------------------------------------------------------
# Кнопки
# ---------------------------------------------------------------------------

MENU_BUTTONS = {
    "webapp": "🔷 Записаться онлайн",
    "quick": "🔹 Быстрая запись",
    "bonuses": "💎 Мои бонусы",
    "contacts": "📍 Контакты и маршрут",
    "question": "💬 Задать вопрос",
    "admin": "👑 Панель управления",
    "cancel": "❌ Отмена",
    "back": "↩️ Назад",
    "main": "🏠 В главное меню",
}

ADMIN_MENU_BUTTONS = {
    "requests": "📥 Новые заявки",
    "dialogs": "💬 Открытые диалоги",
    "clients": "👥 База клиентов",
    "broadcast": "📢 Сделать рассылку",
    "services": "⚙️ Услуги и цены",
    "promos": "🎁 Промокоды и акции",
    "stats": "📊 Статистика",
    "admins": "👤 Админы",
    "exit": "↩️ В клиентское меню",
}

BTN_BACK = MENU_BUTTONS["back"]
BTN_CANCEL = MENU_BUTTONS["cancel"]
BTN_CONFIRM = "✅ Подтвердить"
BTN_SKIP = "⏭ Пропустить"
BTN_MAIN_MENU = "🏠 В главное меню"
BTN_SEND_MASTER = "✅ Отправить мастеру"
BTN_LAUNCH_BROADCAST = "🚀 Запустить рассылку"
BTN_WEBAPP_SHORT = "🚀 Записаться онлайн"
BTN_SHARE_REF = "👥 Поделиться ссылкой с другом"
BTN_WEBAPP_BONUS = "🚀 Записаться и списать бонусы"

FSM_CANCELLED = "↩️ Ок, отменили. Вы снова в меню."
ERROR_GLOBAL = (
    "⚠️ Произошла ошибка. Попробуйте ещё раз или напишите чуть позже."
)

# ---------------------------------------------------------------------------
# Быстрая запись
# ---------------------------------------------------------------------------

QUICK_PHONE_PROMPT = (
    "Оставьте ваш номер, и дежурный мастер перезвонит для подбора времени:"
)
QUICK_NOTE_PROMPT = (
    "Напишите марку авто или причину обращения (или нажмите пропустить):"
)
QUICK_CREATED = (
    "✅ <b>Запрос на звонок принят!</b>\n\n"
    "Мастер перезвонит вам в ближайшее время."
)
QUICK_NOTE_SKIPPED = "клиент пропустил шаг"

# ---------------------------------------------------------------------------
# Вопрос мастеру
# ---------------------------------------------------------------------------

QUESTION_PROMPT = (
    "Напишите ваш вопрос. Можно прикрепить фото или аудио повреждения:"
)
QUESTION_CONFIRM = (
    "📨 <b>Проверьте вопрос</b>\n\n"
    "{text}\n\n"
    "━━━━━━━━━━━━━━━━\n"
    "Отправляем мастеру?"
)
QUESTION_CREATED = (
    "Вопрос передан в ремзону. Ответ мастера придёт прямо в этот чат."
)
QUESTION_EMPTY = "Напишите вопрос текстом или прикрепите фото / аудио."
QUESTION_MEDIA_CAPTION = "Вложение: {kind}"

# ---------------------------------------------------------------------------
# Mini App
# ---------------------------------------------------------------------------

MINIAPP_CREATED = (
    "✅ <b>Заявка №{request_id} принята!</b>\n\n"
    "Мастер свяжется с вами в течение 10 минут для подтверждения."
)
MINIAPP_BAD_DATA = "⚠️ Не удалось прочитать данные из приложения. Попробуйте ещё раз."

# ---------------------------------------------------------------------------
# Бонусы
# ---------------------------------------------------------------------------

BONUSES_CARD = (
    "🎁 <b>Мои бонусы</b>\n\n"
    "🪪 {full_name}\n"
    "📱 {phone}\n"
    "💰 Баланс бонусов: <b>{balance} ₽</b>\n"
    "🚗 Визитов: <b>{visits}</b>\n\n"
    "━━━━━━━━━━━━━━━━\n"
    "🔗 Реферальная ссылка:\n"
    "<code>{ref_link}</code>\n\n"
    "👥 Пригласите друга — он получит 10% на первый визит, "
    "а вы — бесплатную диагностику!"
)
INVITE_SHARE_TEXT = (
    "Записывайся в Экотек Сервис — скидка 10% на первый визит: {link}"
)

BONUS_FREE_DIAG = "🔍 Бесплатная диагностика"
BONUS_LOYALTY_2ND = "🎉 Скидка 10% на 2-й визит"
BONUS_REFERRAL_10 = "🎁 Скидка 10% на первый визит"
BONUS_EMPTY = "Пока пусто"
BONUSES_PROMO_UNLIMITED = "бессрочно"
BONUSES_NO_PROMOS = "Сейчас дополнительных акций нет."
BONUSES_PROMO_ITEM = (
    "🏷 <b>{title}</b>\n{description}\nСкидка: <b>{discount}</b>\nСрок: {valid_until}"
)

# ---------------------------------------------------------------------------
# Контакты
# ---------------------------------------------------------------------------

CONTACTS_TEXT = (
    "📍 <b>{service_name}</b>\n\n"
    "🏠 Адрес: {address}\n"
    "🕒 График работы: {hours}\n"
    "📞 Прямой телефон мастера-приёмщика: <code>{phone}</code>"
)
CONTACTS_MAPS_BUTTON = "🗺 Построить маршрут (Яндекс Карты)"
CONTACTS_PHONE_BUTTON = "📞 Позвонить на сервис"

# ---------------------------------------------------------------------------
# Рефералы
# ---------------------------------------------------------------------------

REFERRAL_NOTIFICATION = (
    "🎉 <b>По вашей ссылке пришёл друг!</b>\n\n"
    "Вам начислена <b>бесплатная диагностика</b>."
)
REFERRAL_WELCOME = (
    "🎁 <b>Вам подарок от друга!</b>\n\n"
    "Скидка 10% на первый визит уже в профиле."
)
LOYALTY_INVITER_REWARD = REFERRAL_NOTIFICATION
LOYALTY_REFERRAL_APPLIED = REFERRAL_WELCOME
LOYALTY_REFERRAL_SELF = "Свою ссылку использовать нельзя — отправьте её другу."
LOYALTY_REFERRAL_ALREADY = "Реферальный код уже был применён ранее."
LOYALTY_REFERRAL_INVALID = "Реферальный код не найден. Проверьте ссылку."
DISCOUNT_LINE_LOYALTY = "🎉 Учтена скидка 10% на 2-й визит"
DISCOUNT_LINE_REFERRAL = "🎁 Учтена скидка 10% на первый визит"
DISCOUNT_LINE_FREE_DIAG = "🔍 Учтена бесплатная диагностика"

# ---------------------------------------------------------------------------
# Категории
# ---------------------------------------------------------------------------

SERVICE_CATEGORIES = {
    "maintenance": "🛠 ТО",
    "suspension": "🔧 Подвеска",
    "diagnostics": "🔍 Диагностика",
    "electrical": "⚡ Электрика",
    "brakes": "🛑 Тормозная система",
    "engine": "⚙️ ДВС",
    "tires": "🛞 Шиномонтаж",
    "tuning": "🏎 Тюнинг",
    "overhaul": "⚙️ Капремонт",
}

WEBAPP_CATEGORY_ORDER = (
    "maintenance",
    "suspension",
    "diagnostics",
    "electrical",
    "brakes",
    "engine",
    "tires",
)

REQUEST_TYPE_LABELS = {
    "booking": "запись",
    "price": "цена",
    "question": "вопрос",
}

REQUEST_SOURCE_LABELS = {
    "miniapp": "Mini App",
    "quick": "Быстрая",
    "question": "Вопрос",
}

REQUEST_STATUS_LABELS = {
    "new": "Новая",
    "in_progress": "В работе",
    "answered": "Отвечена",
    "closed": "Закрыта",
}

PRICE_FROM = "от {price_from} ₽"
PRICE_RANGE = "от {price_from} ₽ до {price_to} ₽"
PRICE_ON_REQUEST = "по запросу"

# ---------------------------------------------------------------------------
# Диалог мастер ↔ клиент
# ---------------------------------------------------------------------------

MASTER_TO_CLIENT = (
    "🔷 <b>Сообщение от автосервиса по заявке №{id}:</b>\n\n"
    "{reply}"
)
BOOKING_CONFIRMED = (
    "🔷 Ваша запись №{id} на {slot} подтверждена! Ждем вас в автосервисе."
)
CONTACT_MASTER_PROMPT = (
    "Напишите вопрос мастерам по заявке №{id}.\n"
    "Сообщение уйдёт в автосервис вместе с вашим контактом."
)
CONTACT_MASTER_SENT = "✅ Вопрос передан мастерам. Ответ придёт в этот чат."
CONTACT_MASTER_ADMIN = (
    "💬 <b>Вопрос клиента по заявке Mini App №{id}</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "👤 Клиент: {name} ({username})\n"
    "📱 Телефон: {phone}\n"
    "🆔 Telegram: <code>{tg_id}</code>\n\n"
    "{text}"
)
BOOKING_REVOKED_CLIENT = (
    "Заявка №{id} отозвана. Если нужно другое время — запишитесь заново через приложение."
)
BOOKING_REVOKED_ADMIN = (
    "⚠️ <b>Клиент отозвал заявку №{id}</b>\n"
    "Действие: {action}\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "👤 Клиент: {name} ({username})\n"
    "📱 Телефон: {phone}\n"
    "🆔 Telegram: <code>{tg_id}</code>"
)
BOOKING_REVOKE_NO_ACTIVE = "Активной записи для отмены не найдено."
BOOKING_REVOKE_TOAST = "Заявка отозвана"
CLIENT_DIALOG_CLOSED = "🔒 Вопрос по заявке №{request_id} закрыт. Спасибо!"
QUESTION_FOLLOWUP_PROMPT = "Напишите сообщение мастеру по заявке №{id}:"

# ---------------------------------------------------------------------------
# Админ-панель
# ---------------------------------------------------------------------------

ADMIN_MENU = "👑 <b>Панель управления «{service_name}»</b>"
ADMIN_ACCESS_DENIED = "🚫 Недостаточно прав. Этот раздел только для администраторов."

ADMIN_REQUESTS_EMPTY = "📭 Новых заявок нет."
ADMIN_DIALOGS_EMPTY = "📭 Открытых диалогов нет."
ADMIN_REQUESTS_HEADER = "📥 <b>Новые заявки</b> · {count}"
ADMIN_DIALOGS_HEADER = "💬 <b>Открытые диалоги</b> · {count}"
ADMIN_REQUEST_LIST_ITEM = "Заявка #{id} · {source} · {car} · {status}"
ADMIN_REQUEST_NO_CAR = "авто не указано"
ADMIN_REQUEST_NO_SERVICE = "не указаны"
ADMIN_REQUEST_NOT_FOUND = "⚠️ Заявка №{id} не найдена."

ADMIN_REQUEST_DETAIL = (
    "🔔 <b>Заявка #{id}</b>\n"
    "━━━━━━━━━━━━━━━━\n"
    "📌 Источник: {source}\n"
    "📊 Статус: {status}\n"
    "👤 Клиент: {full_name} ({username})\n"
    "📱 Телефон: {phone}\n"
    "🚘 Авто: {car}\n"
    "🛠 Услуги:\n{services}\n"
    "📅 Желаемая дата: {slot}\n"
    "💬 Комментарий: {comment}"
)

ADMIN_MINIAPP_NOTIFY = (
    "🔔 <b>НОВАЯ ЗАПИСЬ #{request_id}</b> (Через Mini App)\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "👤 Клиент: {name} ({username})\n"
    "📱 Телефон: {phone}\n"
    "🚘 Авто: {car}\n"
    "🛠 Выбранные услуги:\n{services}\n"
    "📅 Желаемая дата: {slot}\n"
    "💬 Комментарий: {comment}"
)

ADMIN_QUICK_NOTIFY = (
    "🔥 <b>ЗАКАЗ ЗВОНКА В 1 КЛИК #{request_id}</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "👤 Клиент: {name} ({username})\n"
    "📱 Телефон: {phone}\n"
    "💬 Пожелание: {note}"
)

ADMIN_QUESTION_NOTIFY = (
    "❓ <b>Вопрос мастеру #{request_id}</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "👤 Клиент: {name} ({username})\n"
    "📱 Телефон: {phone}\n"
    "💬 {text}"
)

ADMIN_REPLY_PROMPT = (
    "💬 Напишите текст клиенту по заявке №{id}:"
)
ADMIN_REPLY_SENT = "✅ Сообщение отправлено клиенту."
ADMIN_REPLY_EMPTY = "Сообщение не может быть пустым."
ADMIN_REQUEST_CLOSED = "🔒 Заявка №{request_id} закрыта."
ADMIN_TAKE_IN_PROGRESS = "🛠 Заявка №{id} взята в работу."
BTN_CONFIRM_SLOT = "✅ Подтвердить {slot}"
BTN_CONFIRM_TIME = "✅ Подтвердить время"
BTN_WRITE_CLIENT = "💬 Ответить клиенту"
BTN_WRITE = "💬 Написать"
BTN_CALL = "📞 Позвонить"
BTN_ARCHIVE = "🔒 В архив"
BTN_CALL_NUMBER = "📞 Набрать номер"
BTN_PROCESSED = "🔒 Обработано"
BTN_OPEN_REQUEST = "открыть"

ADMIN_BROADCAST_PROMPT = (
    "📢 Отправьте текст, фото или пост акции для рассылки."
)
ADMIN_BROADCAST_CONFIRM = (
    "📢 <b>Предпросмотр рассылки</b>\n\n"
    "Получателей: <b>{count}</b>\n\n"
    "{text}"
)
ADMIN_BROADCAST_DONE = (
    "✅ Рассылка завершена.\n📨 Отправлено: <b>{ok}</b>\n❌ Ошибок: <b>{fail}</b>"
)
ADMIN_BROADCAST_CANCELLED = "↩️ Рассылка отменена."
ADMIN_BROADCAST_EMPTY = "Нужен текст или фото с подписью."
ADMIN_BROADCAST_PHOTO = "📷 Фото с подписью"

ADMIN_SERVICES_HEADER = "⚙️ <b>Услуги и цены</b> (синхронизация с WebApp)"
ADMIN_SERVICE_ITEM = "{id}. {name} · {price} · {active}"
ADMIN_SERVICE_ACTIVE = "показывать"
ADMIN_SERVICE_INACTIVE = "скрыта"
ADMIN_SERVICE_CREATED = "✅ Услуга «{name}» добавлена."
ADMIN_SERVICE_UPDATED = "✅ Услуга «{name}» обновлена."
ADMIN_SERVICE_DELETED = "🗑 Услуга удалена."
ADMIN_SERVICE_NOT_FOUND = "⚠️ Услуга не найдена."
ADMIN_SERVICE_PROMPT_CATEGORY = "Выберите категорию 👇"
ADMIN_SERVICE_PROMPT_NAME = "Введите название услуги:"
ADMIN_SERVICE_PROMPT_PRICE_FROM = (
    "Введите цену «от» в рублях (целое число) или нажмите «Пропустить»."
)
ADMIN_SERVICE_INVALID_PRICE = "Введите целое неотрицательное число."
BTN_ADD_SERVICE = "➕ Добавить услугу"

ADMIN_PROMO_HEADER = "🎁 <b>Промокоды и акции</b>"
ADMIN_PROMO_ITEM = "{id}. {title} · {discount} · до {valid_until} · {active}"
ADMIN_PROMO_ACTIVE = "активна"
ADMIN_PROMO_INACTIVE = "скрыта"
ADMIN_PROMO_CREATED = "✅ Акция «{title}» добавлена."
ADMIN_PROMO_UPDATED = "✅ Акция «{title}» обновлена."
ADMIN_PROMO_DELETED = "🗑 Акция удалена."
ADMIN_PROMO_NOT_FOUND = "⚠️ Акция не найдена."
ADMIN_PROMO_PROMPT_TITLE = "Введите название акции / промокода:"
ADMIN_PROMO_PROMPT_DESCRIPTION = "Введите описание:"
ADMIN_PROMO_PROMPT_DISCOUNT = "Введите размер скидки, например: 10%."
ADMIN_PROMO_PROMPT_VALID_UNTIL = (
    "Срок действия ДД.ММ.ГГГГ или нажмите «Пропустить»."
)
ADMIN_PROMO_INVALID_DATE = "Некорректная дата. Формат ДД.ММ.ГГГГ."

ADMIN_STATS = (
    "📊 <b>Статистика</b>\n\n"
    "Сегодня: <b>{today}</b> заявок\n"
    "  · Mini App: {today_miniapp}\n"
    "  · Быстрая запись: {today_quick}\n"
    "Неделя: <b>{week}</b>\n"
    "Месяц: <b>{month}</b>"
)

ADMIN_CLIENTS_HEADER = "👥 <b>База клиентов</b> · стр. {page}"
ADMIN_CLIENT_ITEM = "{full_name} · {phone} · визитов: {visits_count}"
ADMIN_CLIENT_SEARCH_PROMPT = "🔎 Введите имя, телефон или госномер:"
ADMIN_CLIENT_NOT_FOUND = "Клиенты по запросу «{query}» не найдены."
ADMIN_CLIENTS_EMPTY = "Клиентов пока нет."
ADMIN_CLIENT_CARD = (
    "👤 <b>Клиент</b>\n\n"
    "🪪 {full_name}\n"
    "🆔 {tg_id}\n"
    "🔗 @{username}\n"
    "📱 {phone}\n"
    "💰 Бонусы: {balance} ₽\n"
    "🚗 Визитов: {visits_count}"
)
ADMIN_FLAG_YES = "да"
ADMIN_FLAG_NO = "нет"
ADMIN_GIFT_TO_CLIENT = "🎁 <b>Подарок от {service_name}!</b>\n\n{text}"
ADMIN_BONUS_PROMPT = "Введите сумму бонусов в рублях (целое число):"
ADMIN_BONUS_ADDED = "✅ Начислено {amount} ₽. Баланс: {balance} ₽."
ADMIN_BONUS_INVALID = "Введите целое число больше нуля."
ADMIN_ADMIN_NO_USERNAME = "без username"
PROFILE_NO_PHONE = PHONE_NOT_BOUND

ADMIN_ADMINS_HEADER = "👤 <b>Администраторы</b>"
ADMIN_ADMINS_ITEM = "{full_name} · {tg_id} · @{username}"
ADMIN_ADMIN_ADD_PROMPT = "Отправьте Telegram ID нового администратора."
ADMIN_ADMIN_ADDED = "✅ Пользователь {tg_id} назначен администратором."
ADMIN_ADMIN_EXISTS = "Пользователь {tg_id} уже администратор."
ADMIN_ADMIN_NOT_FOUND = "Пользователь {tg_id} ещё не запускал бота."
ADMIN_ADMIN_REMOVED = "✅ Пользователь {tg_id} снят с роли."
ADMIN_ADMIN_CANNOT_REMOVE_OWNER = "Владельца нельзя снять."
ADMIN_INVALID_TG_ID = "Укажите корректный числовой Telegram ID."
ADMIN_NEW_ADMIN_GRANTED = (
    "👑 Вам выданы права администратора в <b>{service_name}</b>."
)

ADMIN_ESCALATION_30 = "⏰ Заявка №{request_id} без ответа уже 30 минут."
ADMIN_ESCALATION_120 = "🚨 Заявка №{request_id} ждёт ответа 2 часа."
INACTIVE_CLIENT_REMINDER = (
    "👋 Давно не виделись! Пора заехать на ТО — запишитесь в пару касаний."
)

# Совместимость со старыми импортами
MENU_MAIN = START_GREETING
ADMIN_WELCOME = ADMIN_MENU
SHARE_PHONE_REQUEST = QUICK_PHONE_PROMPT
PHONE_RECEIVED = "✅ Номер сохранён."
BOOKING_CANCELLED = FSM_CANCELLED
PRICE_CANCELLED = FSM_CANCELLED
QUESTION_CANCELLED = FSM_CANCELLED
ADMIN_REPLY_TO_CLIENT = MASTER_TO_CLIENT
ADMIN_REQUEST_CARD = ADMIN_REQUEST_DETAIL
ADMIN_NEW_REQUEST = ADMIN_MINIAPP_NOTIFY
ADMIN_SERVICE_PROMPT_DESCRIPTION = "Описание (или пропустите):"
ADMIN_SERVICE_PROMPT_PRICE_TO = "Цена «до» (или пропустите):"
BTN_ADD_PROMO = "➕ Добавить акцию"
BTN_ADD_ADMIN = "➕ Назначить админа"
