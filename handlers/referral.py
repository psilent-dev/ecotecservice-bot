"""Хелперы реферальной программы."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.repo import UserRepo
from texts import (
    LOYALTY_REFERRAL_ALREADY,
    LOYALTY_REFERRAL_APPLIED,
    LOYALTY_REFERRAL_INVALID,
    LOYALTY_REFERRAL_SELF,
)

_REF_PREFIX = "ref_"
_REF_CODE_RE = re.compile(r"^[A-Z2-7]{8}$")


class ReferralOutcome:
    """Результат попытки привязать реферальный код."""

    def __init__(
        self,
        *,
        referrer: User | None = None,
        client_message: str | None = None,
    ) -> None:
        self.referrer = referrer
        self.client_message = client_message

    @property
    def applied(self) -> bool:
        """Код принят и связка создана."""
        return self.referrer is not None


def parse_ref_code(start_param: str | None) -> str | None:
    """Извлекает 8-символьный код из deep-link `ref_XXXXXXXX`."""
    if start_param is None:
        return None
    raw = start_param.strip()
    if not raw:
        return None
    if raw.lower().startswith(_REF_PREFIX):
        raw = raw[len(_REF_PREFIX) :]
    code = raw.strip().upper()
    if _REF_CODE_RE.fullmatch(code) is None:
        return None
    return code


async def get_by_referral_code(session: AsyncSession, code: str) -> User | None:
    """Ищет пользователя по реферальному коду."""
    result = await session.execute(
        select(User).where(User.referral_code == code.upper())
    )
    return result.scalar_one_or_none()


async def apply_referral(
    session: AsyncSession,
    new_user: User,
    ref_code: str,
) -> ReferralOutcome:
    """Связывает новичка с пригласившим и активирует награды лояльности."""
    if new_user.referral_code.upper() == ref_code.upper():
        return ReferralOutcome(client_message=LOYALTY_REFERRAL_SELF)

    referrer = await get_by_referral_code(session, ref_code)
    if referrer is None:
        return ReferralOutcome(client_message=LOYALTY_REFERRAL_INVALID)
    if referrer.id == new_user.id:
        return ReferralOutcome(client_message=LOYALTY_REFERRAL_SELF)
    if new_user.referred_by_id is not None:
        return ReferralOutcome(client_message=LOYALTY_REFERRAL_ALREADY)

    linked = await UserRepo.set_referred_by(session, new_user.id, referrer.id)
    if linked is None:
        return ReferralOutcome(client_message=LOYALTY_REFERRAL_ALREADY)

    await UserRepo.activate_discount_10(session, new_user.id)
    await UserRepo.activate_free_diagnostics(session, referrer.id)
    await session.refresh(new_user)
    await session.refresh(referrer)
    return ReferralOutcome(referrer=referrer, client_message=LOYALTY_REFERRAL_APPLIED)
