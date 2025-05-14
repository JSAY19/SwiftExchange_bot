import enum
from decouple import config
import asyncio
import datetime
from sqlalchemy import BigInteger, ForeignKey, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine

DATABASE_URL = config("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=False)

async_session_ = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Role(enum.Enum):
    admin = "Админ"
    manager = "Менеджер"
    client = "Клиент"


class Status(enum.Enum):
    creation = "Создание"
    pending_payment = "Ожидание оплаты"
    processing = "Обработка"
    successful = "Успешно"
    cancelled = "Отменен"
    pending_get = "Ожидание получения"


class UserTable(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id = mapped_column(BigInteger)
    username: Mapped[str] = mapped_column(nullable=True)
    role: Mapped[Role]


class ExchangeHistoryTable(Base):
    __tablename__ = 'exchanges_history'

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[Status]
    rate: Mapped[str]
    currency_to: Mapped[str]
    currency_from: Mapped[str]
    get: Mapped[float]
    give: Mapped[float]
    date: Mapped[datetime.datetime] = mapped_column(server_default=text("TIMEZONE('utc', now())"))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


if __name__ == '__main__':
    asyncio.run(async_main())