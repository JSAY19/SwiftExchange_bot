import enum
from decouple import config  # Убедись, что у тебя есть .env файл с DATABASE_URL или переменная окружения
import asyncio
import datetime
from sqlalchemy import BigInteger, ForeignKey, text, select, desc  # Добавили select, desc
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
import logging

# DATABASE_URL = config("DATABASE_URL") # Раскомментируй, если используешь decouple

# --- Заглушка для DATABASE_URL, если decouple не настроен для примера ---
# УДАЛИ ЭТО В СВОЕМ ПРОЕКТЕ И ИСПОЛЬЗУЙ decouple
try:
    DATABASE_URL = config("DATABASE_URL")
except Exception:
    print("WARNING: DATABASE_URL not found via decouple. Using a default SQLite for example.")
    DATABASE_URL = "sqlite+aiosqlite:///./test_temp.db"
# --- Конец заглушки ---


engine = create_async_engine(DATABASE_URL, echo=False)
async_session_ = async_sessionmaker(engine, expire_on_commit=False)  # Устанавливаем expire_on_commit=False по умолчанию


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
    successful = "Успешно"  # Опечатка исправлена с "Успешно" на "successful" как значение, если нужно
    cancelled = "Отменен"
    pending_get = "Ожидание получения"


class UserTable(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id = mapped_column(BigInteger, unique=True)  # Добавил unique=True, т.к. tg_id обычно уникален
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
    # Обрати внимание: здесь нет явного relationship 'user'
    # Если бы было:
    # from sqlalchemy.orm import relationship
    # user: Mapped["UserTable"] = relationship()


# --- Вспомогательная функция ---
async def _get_user_id_by_tg_id(session, tg_id: int) -> int | None:
    """Получает внутренний ID пользователя по его Telegram ID."""
    stmt = select(UserTable.id).where(UserTable.tg_id == tg_id)
    user_id = await session.scalar(stmt)
    return user_id


# --- Пользователи ---
async def set_user(tg_id: int, username: str = None) -> bool:
    """
    Запись или обновление пользователя в БД.
    Возвращает True если пользователь успешно создан/обновлен, False в случае ошибки.
    """
    try:
        async with async_session_() as session:
            async with session.begin():
                stmt = select(UserTable).where(UserTable.tg_id == tg_id)
                user = await session.scalar(stmt)

                if not user:
                    user = UserTable(tg_id=tg_id, role=Role.client, username=username)
                    session.add(user)
                    logging.info(f"User {tg_id} created successfully.")
                elif user.username != username:  # Обновляем имя пользователя только если оно изменилось
                    user.username = username
                    logging.info(f"User {tg_id} username updated to '{username}'.")
                else:
                    logging.info(f"User {tg_id} already exists with username '{username}'. No update needed.")
                return True
    except Exception as e:
        logging.error(f"Error in set_user for tg_id {tg_id}: {str(e)}")
        return False


async def get_user_role(tg_id: int) -> Role | None:
    """Получение роли пользователя."""
    async with async_session_() as session:
        stmt = select(UserTable.role).where(UserTable.tg_id == tg_id)
        role = await session.scalar(stmt)
        return role


# --- Заявки (Exchange History) ---

async def create_exchange_request(
        tg_id: int,
        currency_from: str,
        currency_to: str,
        give: float,
        rate: str,
        get: float,
) -> ExchangeHistoryTable | None:
    """
    Создает новую заявку на обмен со статусом 'Создание'.
    Возвращает созданную заявку или None, если пользователь не найден.
    """
    async with async_session_() as session:
        async with session.begin():
            user_id = await _get_user_id_by_tg_id(session, tg_id)
            if not user_id:
                print(f"User with tg_id {tg_id} not found. Cannot create exchange request.")
                return None

            new_request = ExchangeHistoryTable(
                user_id=user_id,
                status=Status.creation,
                rate=rate,
                currency_to=currency_to,
                currency_from=currency_from,
                get=get,
                give=give,
            )
            session.add(new_request)
            await session.flush()  # Чтобы получить ID и server_default значения (например, date)
            print(f"Created new exchange request {new_request.id} for user_id {user_id}")
            return new_request


async def get_active_exchange_request(tg_id: int) -> ExchangeHistoryTable | None:
    """
    Получает активную заявку пользователя (статус 'Создание').
    """
    async with async_session_() as session:
        user_id = await _get_user_id_by_tg_id(session, tg_id)
        if not user_id:
            return None

        stmt = (
            select(ExchangeHistoryTable)
            .where(
                ExchangeHistoryTable.user_id == user_id,
                ExchangeHistoryTable.status == Status.creation,
            )
            .order_by(ExchangeHistoryTable.date.desc())
        )
        active_request = await session.scalar(stmt)
        return active_request


async def update_exchange_request_data(request_id: int, **kwargs) -> ExchangeHistoryTable | None:
    """
    Обновляет данные указанной заявки.
    """
    async with async_session_() as session:
        async with session.begin():
            stmt_select = select(ExchangeHistoryTable).where(ExchangeHistoryTable.id == request_id)
            request_to_update = await session.scalar(stmt_select)

            if not request_to_update:
                print(f"Exchange request with id {request_id} not found.")
                return None

            for key, value in kwargs.items():
                if hasattr(request_to_update, key):
                    setattr(request_to_update, key, value)
                else:
                    print(f"Warning: Attribute '{key}' not found in ExchangeHistoryTable model.")

            await session.flush()  # Убедимся, что изменения записаны перед возвратом
            print(f"Exchange request {request_id} updated with {kwargs}")
            return request_to_update


async def get_exchange_request_by_id(request_id: int) -> ExchangeHistoryTable | None:
    """
    Получает заявку по её ID, включая связанного пользователя.
    К объекту ExchangeHistoryTable будет динамически добавлен атрибут 'user'.
    """
    async with async_session_() as session: # async_session_ уже с expire_on_commit=False
        stmt = (
            select(ExchangeHistoryTable, UserTable)
            .join(UserTable, ExchangeHistoryTable.user_id == UserTable.id)
            .where(ExchangeHistoryTable.id == request_id)
        )
        db_result = await session.execute(stmt)
        row = db_result.first() # Ожидаем одну запись или None

        if row:
            exchange_record: ExchangeHistoryTable = row[0]
            user_record: UserTable = row[1]
            setattr(exchange_record, 'user', user_record) # Динамически добавляем пользователя
            return exchange_record
        return None


async def get_user_exchange_history(
        tg_id: int, include_creation_status: bool = False
) -> list[ExchangeHistoryTable]:
    """
    Получает историю заявок пользователя.
    """
    async with async_session_() as session:
        user_id = await _get_user_id_by_tg_id(session, tg_id)
        if not user_id:
            return []

        stmt = select(ExchangeHistoryTable).where(ExchangeHistoryTable.user_id == user_id)

        if not include_creation_status:
            stmt = stmt.where(ExchangeHistoryTable.status != Status.creation)

        stmt = stmt.order_by(ExchangeHistoryTable.date.desc())
        result = await session.execute(stmt)
        history = result.scalars().all()
        return list(history)


async def get_last_20_all_users_exchange_history() -> list[ExchangeHistoryTable]:
    """
    Получает последние 20 записей истории обменов всех пользователей.
    К каждому объекту ExchangeHistoryTable будет динамически добавлен атрибут 'user',
    содержащий соответствующий объект UserTable.
    """
    async with async_session_() as session:
        stmt = (
            select(ExchangeHistoryTable, UserTable)  # Выбираем обе таблицы
            .join(UserTable, ExchangeHistoryTable.user_id == UserTable.id)  # Соединяем их по user_id
            .order_by(desc(ExchangeHistoryTable.date))  # Сортируем по дате (новые сначала)
            .limit(20)  # Ограничиваем результат 20 записями
        )

        db_result = await session.execute(stmt)

        processed_history: list[ExchangeHistoryTable] = []
        # db_result.all() возвращает список объектов Row, где каждый Row - это кортеж (ExchangeHistoryTable_instance, UserTable_instance)
        for row in db_result.all():
            exchange_record: ExchangeHistoryTable = row[0]
            user_record: UserTable = row[1]

            # Динамически присваиваем объект пользователя атрибуту 'user' объекта обмена.
            # Это позволит использовать `exchange_record.user` в вызывающем коде (например, в main).
            # Python - динамический язык, поэтому это сработает во время выполнения.
            # Однако, статические анализаторы типов (типа MyPy) могут выдать предупреждение,
            # т.к. атрибут 'user' не определен статически в классе ExchangeHistoryTable.
            setattr(exchange_record, 'user', user_record)
            # или можно просто exchange_record.user = user_record

            processed_history.append(exchange_record)

        return processed_history


# --- Пример использования (main) ---
async def main_test_logic():  # Переименовал, чтобы не конфликтовать с async_main для создания таблиц
    # Создадим несколько пользователей и заявок для теста
    user1_tg_id = 11111
    user2_tg_id = 22222
    user3_tg_id = 123456789  # Используем этот ID для более поздних тестов

    await set_user(tg_id=user1_tg_id, username="user_one")
    await set_user(tg_id=user2_tg_id, username="user_two")
    await set_user(tg_id=user3_tg_id, username="testuser_main_run")

    print("\n--- Создание тестовых заявок ---")
    # Создаем заявки, чтобы их было больше 20 для проверки лимита
    for i in range(12):  # 12 заявок для первого пользователя
        req = await create_exchange_request(
            tg_id=user1_tg_id,
            currency_from="BTC", currency_to="USD",
            give=round(0.1 + i * 0.01, 4), rate=str(50000 + i * 100),
            get=round((0.1 + i * 0.01) * (50000 + i * 100), 2)
        )
        if req:  # Сразу меняем статус, чтобы не были 'creation'
            await update_exchange_request_data(req.id, status=Status.successful)
        await asyncio.sleep(0.01)  # Небольшая пауза, чтобы даты немного отличались

    for i in range(13):  # 13 заявок для второго пользователя
        req = await create_exchange_request(
            tg_id=user2_tg_id,
            currency_from="ETH", currency_to="EUR",
            give=round(1.0 + i * 0.1, 4), rate=str(3000 + i * 50),
            get=round((1.0 + i * 0.1) * (3000 + i * 50), 2)
        )
        if req:
            await update_exchange_request_data(req.id,
                                               status=Status.pending_payment if i % 2 == 0 else Status.cancelled)
        await asyncio.sleep(0.01)  # Небольшая пауза

    print("--- Тестовые заявки созданы ---\n")

    print("\n--- Тестирование get_last_20_all_users_exchange_history ---")
    last_20_exchanges = await get_last_20_all_users_exchange_history()

    if not last_20_exchanges:
        print("No exchange history found for all users.")
    else:
        print(f"Found {len(last_20_exchanges)} exchange records (max 20):")
        for item in last_20_exchanges:
            # Так как мы динамически добавили атрибут 'user'
            user_info = f"User TG ID: {item.user.tg_id if hasattr(item, 'user') and item.user else 'N/A'}"
            date_str = item.date.strftime('%Y-%m-%d %H:%M:%S') if item.date else 'N/A'
            print(
                f"  ID: {item.id}, {user_info}, Status: {item.status.value}, "
                f"From: {item.give} {item.currency_from} To: {item.get} {item.currency_to}, "
                f"Rate: {item.rate}, Date: {date_str}"
            )
    print("--- Конец теста get_last_20_all_users_exchange_history ---\n")

    # Остальной код из твоего примера main для демонстрации других функций
    user_tg_id_main = user3_tg_id  # Используем уже созданного пользователя

    user_role = await get_user_role(tg_id=user_tg_id_main)
    print(f"User {user_tg_id_main} Role: {user_role.value if user_role else 'Not found'}")

    active_req = await get_active_exchange_request(tg_id=user_tg_id_main)
    if active_req:
        print(f"Found active request for {user_tg_id_main}: ID {active_req.id}, Status {active_req.status.value}")
    else:
        print(f"No active request found for {user_tg_id_main}. Creating a new one...")
        active_req = await create_exchange_request(
            tg_id=user_tg_id_main,
            currency_from="LTC",
            currency_to="USDT",
            give=0.0,
            rate="N/A",
            get=0.0
        )
        if active_req:
            print(
                f"Created new active request for {user_tg_id_main}: ID {active_req.id}, Status {active_req.status.value}")

    if active_req:
        print(f"\nUpdating active request {active_req.id} for {user_tg_id_main}...")
        updated_req = await update_exchange_request_data(
            request_id=active_req.id,
            give=10.5,
            currency_from="LTC_updated",
            rate="150.0"
        )
        if updated_req:
            calculated_get = round(updated_req.give * float(updated_req.rate) if updated_req.rate != "N/A" else 0.0, 2)
            final_updated_req = await update_exchange_request_data(
                request_id=updated_req.id,
                get=calculated_get
            )
            if final_updated_req:
                print(
                    f"Updated request {final_updated_req.id}: Give={final_updated_req.give}, Get={final_updated_req.get}, Rate={final_updated_req.rate}")
                active_req = final_updated_req

        if active_req:
            print(f"\nChanging status of request {active_req.id} to 'Pending Payment'...")
            finalized_req = await update_exchange_request_data(
                request_id=active_req.id,
                status=Status.pending_payment
            )
            if finalized_req:
                print(f"Request {finalized_req.id} status is now: {finalized_req.status.value}")

    print(f"\nUser {user_tg_id_main} exchange history (excluding 'creation'):")
    history = await get_user_exchange_history(tg_id=user_tg_id_main)
    if not history:
        print("No history found.")
    for item in history:
        print(
            f"  ID: {item.id}, Status: {item.status.value}, From: {item.give} {item.currency_from} "
            f"To: {item.get} {item.currency_to}, Rate: {item.rate}, Date: {item.date.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    # Создадим еще одну заявку в статусе 'creation' для этого пользователя
    await create_exchange_request(
        tg_id=user_tg_id_main, currency_from="XMR", currency_to="BTC",
        give=5.0, rate="0.005", get=0.025
    )

    print(f"\nUser {user_tg_id_main} exchange history (including 'creation'):")
    full_history = await get_user_exchange_history(tg_id=user_tg_id_main, include_creation_status=True)
    if not full_history:
        print("No history found.")
    for item in full_history:
        print(
            f"  ID: {item.id}, Status: {item.status.value}, From: {item.give} {item.currency_from} "
            f"To: {item.get} {item.currency_to}, Rate: {item.rate}, Date: {item.date.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    if full_history:
        # Возьмем ID последней созданной заявки (она должна быть первой в списке из-за сортировки)
        first_req_id = full_history[0].id
        print(f"\nGetting request by ID: {first_req_id}")
        specific_request = await get_exchange_request_by_id(first_req_id)
        if specific_request:
            print(
                f"  Found: ID {specific_request.id}, Status {specific_request.status.value}, Date: {specific_request.date.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"  Request with ID {first_req_id} not found.")



if __name__ == '__main__':
    # Затем запускаем основную тестовую логику
    asyncio.run(main_test_logic())