"""Валидация телефона, Telegram ID и генерация реферального кода."""

from __future__ import annotations

import base64
import re
import secrets

_PHONE_DIGITS_RE = re.compile(r"\D")


def normalize_phone(raw: str) -> str | None:
    """Приводит номер к формату +7XXXXXXXXXX.

    Принимает 8XXXXXXXXXX, 7XXXXXXXXXX, 9XXXXXXXXX и варианты с пробелами,
    скобками и дефисами. Возвращает None, если номер распознать нельзя.
    """
    digits = _PHONE_DIGITS_RE.sub("", raw)
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    elif len(digits) == 10 and digits.startswith("9"):
        digits = "7" + digits
    if len(digits) == 11 and digits.startswith("7"):
        return f"+{digits}"
    return None


def generate_referral_code() -> str:
    """Возвращает 8 символов Crockford-совместимого base32 в верхнем регистре."""
    # 5 байт → ровно 8 символов base32 без паддинга.
    encoded = base64.b32encode(secrets.token_bytes(5)).decode("ascii")
    return encoded.rstrip("=").upper()


def format_phone_display(phone: str | None) -> str:
    """Красивый номер: +7 (999) 000-00-00."""
    if not phone:
        return ""
    digits = _PHONE_DIGITS_RE.sub("", phone)
    if len(digits) == 11 and digits.startswith("7"):
        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    return phone


def tel_href(phone: str | None) -> str | None:
    """Нормализованный tel:+7… для ссылок (Telegram часто отклоняет такой URL)."""
    if not phone:
        return None
    normalized = normalize_phone(phone)
    return f"tel:{normalized}" if normalized else None


def is_valid_tg_id(s: str) -> bool:
    """Проверяет, что строка — положительный целочисленный Telegram ID."""
    value = s.strip()
    if not value.isdigit():
        return False
    try:
        return int(value) > 0
    except ValueError:
        return False
