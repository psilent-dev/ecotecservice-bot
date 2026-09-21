"""ORM-модели и перечисления предметной области автосервиса."""

from __future__ import annotations

import enum
from datetime import date, datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


def utc_now() -> datetime:
    """Возвращает текущее время в UTC."""
    return datetime.now(timezone.utc)


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Сохраняет в БД значения enum, а не имена констант."""
    return [item.value for item in enum_cls]


class ServiceCategory(str, enum.Enum):
    """Категории услуг автосервиса."""

    DIAGNOSTICS = "diagnostics"
    MAINTENANCE = "maintenance"
    SUSPENSION = "suspension"
    ELECTRICAL = "electrical"
    TIRES = "tires"
    BRAKES = "brakes"
    ENGINE = "engine"
    TUNING = "tuning"
    OVERHAUL = "overhaul"

    def label(self) -> str:
        """Русское название категории с эмодзи-маркером для меню."""
        from texts import SERVICE_CATEGORIES

        return SERVICE_CATEGORIES.get(self.value, self.value)


class RequestType(str, enum.Enum):
    """Тип обращения клиента."""

    BOOKING = "booking"
    PRICE = "price"
    QUESTION = "question"


class RequestSource(str, enum.Enum):
    """Откуда пришла заявка."""

    MINIAPP = "miniapp"
    QUICK = "quick"
    QUESTION = "question"


class RequestStatus(str, enum.Enum):
    """Статус обработки заявки."""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    ANSWERED = "answered"
    CLOSED = "closed"


class User(Base):
    """Клиент или администратор Telegram-бота."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    referral_code: Mapped[str] = mapped_column(String(8), unique=True, index=True, nullable=False)
    referred_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    free_diagnostics: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    discount_10_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    visits_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    loyalty_discount_2nd: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    bonus_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    referred_by: Mapped[User | None] = relationship(
        "User",
        remote_side="User.id",
        foreign_keys=[referred_by_id],
        back_populates="referrals",
    )
    referrals: Mapped[list[User]] = relationship(
        "User",
        foreign_keys=[referred_by_id],
        back_populates="referred_by",
    )
    requests: Mapped[list[ClientRequest]] = relationship(
        "ClientRequest",
        back_populates="user",
        foreign_keys="ClientRequest.user_id",
    )


class ClientRequest(Base):
    """Заявка клиента: запись, цена или вопрос мастеру."""

    __tablename__ = "client_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[RequestType] = mapped_column(
        Enum(
            RequestType,
            values_callable=_enum_values,
            native_enum=False,
            length=32,
        ),
        nullable=False,
    )
    service: Mapped[ServiceCategory | None] = mapped_column(
        Enum(
            ServiceCategory,
            values_callable=_enum_values,
            native_enum=False,
            length=32,
        ),
        nullable=True,
    )
    car_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[RequestSource] = mapped_column(
        Enum(
            RequestSource,
            values_callable=_enum_values,
            native_enum=False,
            length=32,
        ),
        default=RequestSource.QUICK,
        nullable=False,
        index=True,
    )
    desired_slot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    services_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[RequestStatus] = mapped_column(
        Enum(
            RequestStatus,
            values_callable=_enum_values,
            native_enum=False,
            length=32,
        ),
        default=RequestStatus.NEW,
        nullable=False,
        index=True,
    )
    admin_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    answered_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
    )
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="requests",
    )
    admin: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[answered_by],
    )


class Service(Base):
    """Услуга прайса автосервиса."""

    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[ServiceCategory] = mapped_column(
        Enum(
            ServiceCategory,
            values_callable=_enum_values,
            native_enum=False,
            length=32,
        ),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Promo(Base):
    """Промо-акция сервиса."""

    __tablename__ = "promos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    discount: Mapped[str] = mapped_column(String(64), nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
