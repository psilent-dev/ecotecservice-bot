"""Чистые функции программы лояльности."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ServiceCategory, User
from texts import (
    BONUS_FREE_DIAG,
    BONUS_LOYALTY_2ND,
    BONUS_REFERRAL_10,
    DISCOUNT_LINE_FREE_DIAG,
    DISCOUNT_LINE_LOYALTY,
    DISCOUNT_LINE_REFERRAL,
)


def apply_discounts_to_request_text(
    user: User,
    service_category: ServiceCategory | None,
    text: str,
) -> str:
    """Добавляет к тексту заявки строки о скидках, которые будут применены."""
    lines: list[str] = [text.strip()] if text.strip() else []
    if user.loyalty_discount_2nd:
        lines.append(DISCOUNT_LINE_LOYALTY)
    if user.discount_10_active:
        lines.append(DISCOUNT_LINE_REFERRAL)
    if (
        user.free_diagnostics
        and service_category is ServiceCategory.DIAGNOSTICS
    ):
        lines.append(DISCOUNT_LINE_FREE_DIAG)
    return "\n\n".join(lines)


async def consume_discounts(
    user: User,
    service_category: ServiceCategory | None,
    session: AsyncSession,
) -> None:
    """Сбрасывает использованные флаги и увеличивает счётчик визитов при скидке 2-го визита."""
    if user.free_diagnostics and service_category is ServiceCategory.DIAGNOSTICS:
        user.free_diagnostics = False
    if user.discount_10_active:
        user.discount_10_active = False
    if user.loyalty_discount_2nd:
        user.visits_count += 1
        user.loyalty_discount_2nd = False
    await session.flush()


def get_active_bonuses(user: User) -> list[str]:
    """Список активных бонусов для карточки профиля."""
    bonuses: list[str] = []
    if user.loyalty_discount_2nd:
        bonuses.append(BONUS_LOYALTY_2ND)
    if user.discount_10_active:
        bonuses.append(BONUS_REFERRAL_10)
    if user.free_diagnostics:
        bonuses.append(BONUS_FREE_DIAG)
    return bonuses
