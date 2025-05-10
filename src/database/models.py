import enum
from decouple import config
import asyncio
import datetime
from sqlalchemy import BigInteger, ForeignKey, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine, async_session

DATABASE_URL = config("DATABASE_URL")

print(DATABASE_URL)

engine = create_async_engine(DATABASE_URL, echo=True)

async_session_ = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Role(enum.Enum):
    admin = "admin"
    manager = "manager"
    client = "client"


class Status(enum.Enum):
    creation = "creation"
    pending_payment = "pending payment"
    processing = "processing"
    successful = "successful"
    canceled = "canceled"


class Currency(enum.Enum):
    rub = "RUB"
    thb = "THB"
    usdt = "USDT"



class UserTable(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(nullable=True)
    role: Mapped[Role]


class ExchangeHistoryTable(Base):
    __tablename__ = 'exchanges_history'

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[Status]
    rate: Mapped[str]
    currency_to: Mapped[str]
    currency_from: Mapped[str]
    date: Mapped[datetime.datetime] = mapped_column(server_default=text("TIMEZONE('utc', now())"))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))

async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == '__main__':
    asyncio.run(async_main())