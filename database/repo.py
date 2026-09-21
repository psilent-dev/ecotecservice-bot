"""Асинхронный слой доступа к данным.

Имена методов совпадают с ТЗ; сущности разведены по классам,
чтобы `create` / `get_by_id` / `list_all` не пересекались.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import (
    ClientRequest,
    Promo,
    RequestSource,
    RequestStatus,
    RequestType,
    Service,
    ServiceCategory,
    User,
)
from utils.validators import generate_referral_code


async def _unique_referral_code(session: AsyncSession) -> str:
    """Подбирает свободный 8-символьный реферальный код."""
    for _ in range(16):
        code = generate_referral_code()
        exists = await session.scalar(select(User.id).where(User.referral_code == code))
        if exists is None:
            return code
    raise RuntimeError("Не удалось сгенерировать уникальный реферальный код")


def _today_in_service_tz() -> date:
    """Текущая календарная дата в часовом поясе сервиса."""
    return datetime.now(ZoneInfo(settings.tz)).date()


class UserRepo:
    """Операции с пользователями."""

    @staticmethod
    async def get_by_tg_id(session: AsyncSession, tg_id: int) -> User | None:
        """Возвращает пользователя по Telegram ID."""
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        tg_id: int,
        full_name: str,
        username: str | None = None,
        is_admin: bool = False,
    ) -> User:
        """Создаёт пользователя с уникальным реферальным кодом."""
        user = User(
            tg_id=tg_id,
            full_name=full_name,
            username=username,
            is_admin=is_admin,
            referral_code=await _unique_referral_code(session),
            discount_10_active=True,
        )
        session.add(user)
        await session.flush()
        return user

    @staticmethod
    async def update_phone(session: AsyncSession, tg_id: int, phone: str) -> User | None:
        """Сохраняет нормализованный телефон клиента."""
        user = await UserRepo.get_by_tg_id(session, tg_id)
        if user is None:
            return None
        user.phone = phone
        await session.flush()
        return user

    @staticmethod
    async def set_referred_by(
        session: AsyncSession,
        user_id: int,
        referrer_id: int,
    ) -> User | None:
        """Привязывает клиента к пригласившему, если реферал ещё не указан."""
        if user_id == referrer_id:
            return None
        user = await session.get(User, user_id)
        referrer = await session.get(User, referrer_id)
        if user is None or referrer is None or user.referred_by_id is not None:
            return None
        user.referred_by_id = referrer_id
        await session.flush()
        return user

    @staticmethod
    async def activate_discount_10(session: AsyncSession, user_id: int) -> User | None:
        """Активирует скидку 10% приглашённому другу."""
        user = await session.get(User, user_id)
        if user is None:
            return None
        user.discount_10_active = True
        await session.flush()
        return user

    @staticmethod
    async def activate_free_diagnostics(session: AsyncSession, user_id: int) -> User | None:
        """Выдаёт пригласившему бесплатную диагностику."""
        user = await session.get(User, user_id)
        if user is None:
            return None
        user.free_diagnostics = True
        await session.flush()
        return user

    @staticmethod
    async def increment_visits(session: AsyncSession, user_id: int) -> User | None:
        """Увеличивает счётчик визитов; после первого визита включает скидку на второй."""
        user = await session.get(User, user_id)
        if user is None:
            return None
        user.visits_count += 1
        if user.visits_count == 1:
            user.loyalty_discount_2nd = True
        await session.flush()
        return user

    @staticmethod
    async def reset_loyalty_discount(session: AsyncSession, user_id: int) -> User | None:
        """Сбрасывает флаг скидки на второй визит после использования."""
        user = await session.get(User, user_id)
        if user is None:
            return None
        user.loyalty_discount_2nd = False
        await session.flush()
        return user

    @staticmethod
    async def get_referral_count(session: AsyncSession, user_id: int) -> int:
        """Считает, сколько клиентов пришло по ссылке пользователя."""
        result = await session.scalar(
            select(func.count()).select_from(User).where(User.referred_by_id == user_id)
        )
        return int(result or 0)

    @staticmethod
    async def get_all_admins(session: AsyncSession) -> list[User]:
        """Возвращает всех пользователей с правами администратора."""
        result = await session.execute(
            select(User).where(User.is_admin.is_(True)).order_by(User.id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_clients(session: AsyncSession, offset: int, limit: int) -> list[User]:
        """Постраничный список клиентов, новые сверху."""
        result = await session.execute(
            select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def search_clients(session: AsyncSession, query: str) -> list[User]:
        """Ищет клиентов по имени, username, телефону или Telegram ID."""
        needle = query.strip()
        if not needle:
            return []

        pattern = f"%{needle.lower()}%"
        conditions = [
            func.lower(User.full_name).like(pattern),
            func.lower(func.coalesce(User.username, "")).like(pattern),
            func.coalesce(User.phone, "").like(f"%{needle}%"),
            User.referral_code == needle.upper(),
        ]
        if needle.lstrip("-").isdigit():
            conditions.append(User.tg_id == int(needle))

        result = await session.execute(
            select(User).where(or_(*conditions)).order_by(User.created_at.desc())
        )
        found = list(result.scalars().all())
        seen = {user.id for user in found}
        plate_result = await session.execute(
            select(User)
            .join(ClientRequest, ClientRequest.user_id == User.id)
            .where(func.lower(func.coalesce(ClientRequest.car_info, "")).like(pattern))
            .order_by(User.created_at.desc())
        )
        for user in plate_result.scalars().all():
            if user.id not in seen:
                found.append(user)
                seen.add(user.id)
        return found

    @staticmethod
    async def add_bonus(session: AsyncSession, user_id: int, amount: int) -> User | None:
        """Начисляет бонусы на баланс клиента."""
        user = await session.get(User, user_id)
        if user is None:
            return None
        user.bonus_balance = max(0, user.bonus_balance + amount)
        await session.flush()
        return user

    @staticmethod
    async def add_admin(session: AsyncSession, tg_id: int) -> User | None:
        """Назначает пользователя администратором, если он уже есть в базе."""
        user = await UserRepo.get_by_tg_id(session, tg_id)
        if user is None:
            return None
        user.is_admin = True
        await session.flush()
        return user

    @staticmethod
    async def remove_admin(session: AsyncSession, tg_id: int) -> User | None:
        """Снимает права администратора. Владельца снять нельзя."""
        if tg_id == settings.owner_id:
            return None
        user = await UserRepo.get_by_tg_id(session, tg_id)
        if user is None:
            return None
        user.is_admin = False
        await session.flush()
        return user


class RequestRepo:
    """Операции с заявками клиентов."""

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        user_id: int,
        request_type: RequestType,
        text: str,
        service: ServiceCategory | None = None,
        car_info: str | None = None,
        source: RequestSource = RequestSource.QUICK,
        desired_slot: str | None = None,
        services_text: str | None = None,
        media_file_id: str | None = None,
        media_type: str | None = None,
    ) -> ClientRequest:
        """Создаёт новую заявку клиента со статусом NEW."""
        request = ClientRequest(
            user_id=user_id,
            type=request_type,
            service=service,
            car_info=car_info,
            text=text,
            source=source,
            desired_slot=desired_slot,
            services_text=services_text,
            media_file_id=media_file_id,
            media_type=media_type,
            status=RequestStatus.NEW,
        )
        session.add(request)
        await session.flush()
        return request

    @staticmethod
    async def get_by_id(session: AsyncSession, request_id: int) -> ClientRequest | None:
        """Возвращает заявку по идентификатору."""
        return await session.get(ClientRequest, request_id)

    @staticmethod
    async def get_user_requests(
        session: AsyncSession,
        user_id: int,
        limit: int,
    ) -> list[ClientRequest]:
        """Последние заявки клиента, новые сверху."""
        result = await session.execute(
            select(ClientRequest)
            .where(ClientRequest.user_id == user_id)
            .order_by(ClientRequest.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_new_requests(session: AsyncSession) -> list[ClientRequest]:
        """Все заявки в статусе NEW, старые первыми."""
        result = await session.execute(
            select(ClientRequest)
            .where(ClientRequest.status == RequestStatus.NEW)
            .order_by(ClientRequest.created_at.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def count_new(session: AsyncSession) -> int:
        """Число заявок в статусе NEW."""
        result = await session.scalar(
            select(func.count()).select_from(ClientRequest).where(
                ClientRequest.status == RequestStatus.NEW
            )
        )
        return int(result or 0)

    @staticmethod
    async def list_by_statuses(
        session: AsyncSession,
        statuses: tuple[RequestStatus, ...],
        *,
        oldest_first: bool = False,
    ) -> list[ClientRequest]:
        """Заявки указанных статусов."""
        stmt = select(ClientRequest).where(ClientRequest.status.in_(statuses))
        if oldest_first:
            stmt = stmt.order_by(ClientRequest.created_at.asc())
        else:
            stmt = stmt.order_by(ClientRequest.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def stats(session: AsyncSession) -> dict[str, int]:
        """Счётчики заявок за день, неделю и месяц в часовом поясе сервиса."""
        now = datetime.now(ZoneInfo(settings.tz))
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)

        async def _count(since: datetime) -> int:
            value = await session.scalar(
                select(func.count()).select_from(ClientRequest).where(
                    ClientRequest.created_at >= since
                )
            )
            return int(value or 0)

        miniapp = await session.scalar(
            select(func.count()).select_from(ClientRequest).where(
                ClientRequest.source == RequestSource.MINIAPP,
                ClientRequest.created_at >= today_start,
            )
        )
        quick = await session.scalar(
            select(func.count()).select_from(ClientRequest).where(
                ClientRequest.source == RequestSource.QUICK,
                ClientRequest.created_at >= today_start,
            )
        )
        return {
            "today": await _count(today_start),
            "week": await _count(week_start),
            "month": await _count(month_start),
            "today_miniapp": int(miniapp or 0),
            "today_quick": int(quick or 0),
        }

    @staticmethod
    async def update_status(
        session: AsyncSession,
        request_id: int,
        status: RequestStatus,
    ) -> ClientRequest | None:
        """Меняет статус заявки."""
        request = await RequestRepo.get_by_id(session, request_id)
        if request is None:
            return None
        request.status = status
        await session.flush()
        return request

    @staticmethod
    async def set_reply(
        session: AsyncSession,
        request_id: int,
        reply: str,
        admin_user_id: int,
    ) -> ClientRequest | None:
        """Сохраняет ответ администратора и переводит заявку в ANSWERED."""
        request = await RequestRepo.get_by_id(session, request_id)
        if request is None:
            return None
        request.admin_reply = reply
        request.answered_by = admin_user_id
        request.answered_at = datetime.now(timezone.utc)
        request.status = RequestStatus.ANSWERED
        await session.flush()
        return request

    @staticmethod
    async def get_stale_new_requests(
        session: AsyncSession,
        minutes: int,
    ) -> list[ClientRequest]:
        """Новые заявки, которые ждут ответа дольше указанного числа минут."""
        threshold = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        result = await session.execute(
            select(ClientRequest)
            .where(
                ClientRequest.status == RequestStatus.NEW,
                ClientRequest.created_at <= threshold,
            )
            .order_by(ClientRequest.created_at.asc())
        )
        return list(result.scalars().all())


class ServiceRepo:
    """Операции с услугами прайса."""

    @staticmethod
    async def get_active_by_category(
        session: AsyncSession,
        category: ServiceCategory,
    ) -> list[Service]:
        """Активные услуги выбранной категории."""
        result = await session.execute(
            select(Service)
            .where(Service.category == category, Service.is_active.is_(True))
            .order_by(Service.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_all(session: AsyncSession) -> list[Service]:
        """Полный список услуг для админ-панели."""
        result = await session.execute(
            select(Service).order_by(Service.category, Service.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(session: AsyncSession, service_id: int) -> Service | None:
        """Возвращает услугу по идентификатору."""
        return await session.get(Service, service_id)

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        category: ServiceCategory,
        name: str,
        description: str | None = None,
        price_from: int | None = None,
        price_to: int | None = None,
        is_active: bool = True,
    ) -> Service:
        """Добавляет услугу в прайс."""
        service = Service(
            category=category,
            name=name,
            description=description,
            price_from=price_from,
            price_to=price_to,
            is_active=is_active,
        )
        session.add(service)
        await session.flush()
        return service

    _UPDATABLE = {
        "category",
        "name",
        "description",
        "price_from",
        "price_to",
        "is_active",
    }

    @staticmethod
    async def update(
        session: AsyncSession,
        service_id: int,
        **fields: object,
    ) -> Service | None:
        """Обновляет разрешённые поля услуги."""
        service = await ServiceRepo.get_by_id(session, service_id)
        if service is None:
            return None
        for key, value in fields.items():
            if key in ServiceRepo._UPDATABLE:
                setattr(service, key, value)
        await session.flush()
        return service

    @staticmethod
    async def delete(session: AsyncSession, service_id: int) -> bool:
        """Удаляет услугу. Возвращает False, если записи нет."""
        service = await ServiceRepo.get_by_id(session, service_id)
        if service is None:
            return False
        await session.delete(service)
        await session.flush()
        return True


class PromoRepo:
    """Операции с промо-акциями."""

    @staticmethod
    async def get_active(session: AsyncSession) -> list[Promo]:
        """Действующие акции: активны и без истёкшего срока."""
        today = _today_in_service_tz()
        result = await session.execute(
            select(Promo)
            .where(
                Promo.is_active.is_(True),
                or_(Promo.valid_until.is_(None), Promo.valid_until >= today),
            )
            .order_by(Promo.id.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_all(session: AsyncSession) -> list[Promo]:
        """Все промо-акции для админ-панели."""
        result = await session.execute(select(Promo).order_by(Promo.id.desc()))
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(session: AsyncSession, promo_id: int) -> Promo | None:
        """Возвращает акцию по идентификатору."""
        return await session.get(Promo, promo_id)

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        title: str,
        description: str,
        discount: str,
        valid_until: date | None = None,
        is_active: bool = True,
    ) -> Promo:
        """Создаёт промо-акцию."""
        promo = Promo(
            title=title,
            description=description,
            discount=discount,
            valid_until=valid_until,
            is_active=is_active,
        )
        session.add(promo)
        await session.flush()
        return promo

    _UPDATABLE = {
        "title",
        "description",
        "discount",
        "valid_until",
        "is_active",
    }

    @staticmethod
    async def update(
        session: AsyncSession,
        promo_id: int,
        **fields: object,
    ) -> Promo | None:
        """Обновляет разрешённые поля акции."""
        promo = await PromoRepo.get_by_id(session, promo_id)
        if promo is None:
            return None
        for key, value in fields.items():
            if key in PromoRepo._UPDATABLE:
                setattr(promo, key, value)
        await session.flush()
        return promo

    @staticmethod
    async def delete(session: AsyncSession, promo_id: int) -> bool:
        """Удаляет акцию. Возвращает False, если записи нет."""
        promo = await PromoRepo.get_by_id(session, promo_id)
        if promo is None:
            return False
        await session.delete(promo)
        await session.flush()
        return True
