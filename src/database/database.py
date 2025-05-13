from src.database.models import (
    async_session_,  # Это твоя фабрика сессий async_sessionmaker(engine)
    UserTable,
    Role,
    ExchangeHistoryTable,
    Status,
)
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
import asyncio
import datetime


# --- Вспомогательная функция ---
async def _get_user_id_by_tg_id(session, tg_id: int) -> int | None:
    """Получает внутренний ID пользователя по его Telegram ID."""
    stmt = select(UserTable.id).where(UserTable.tg_id == tg_id)
    user_id = await session.scalar(stmt)
    return user_id


# --- Пользователи ---
async def set_user(tg_id: int, username: str = None):
    """Запись или обновление пользователя в БД."""
    async with async_session_() as session:
        async with session.begin():
            stmt = select(UserTable).where(UserTable.tg_id == tg_id)
            user = await session.scalar(stmt)

            if not user:
                user = UserTable(tg_id=tg_id, role=Role.client, username=username)
                session.add(user)
                print(f"User {tg_id} created.")
            elif user.username != username:
                user.username = username
                print(f"User {tg_id} username updated.")


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
    Объект будет доступен для чтения атрибутов после закрытия сессии.
    """
    # Используем expire_on_commit=False для этой конкретной сессии
    async with async_session_(expire_on_commit=False) as session:
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
            await session.flush()  # Чтобы получить ID и server_default значения
            print(f"Created new exchange request {new_request.id} for user_id {user_id}")
            # Так как expire_on_commit=False, new_request не будет "истекшим" после коммита
            return new_request


async def get_active_exchange_request(tg_id: int) -> ExchangeHistoryTable | None:
    """
    Получает активную заявку пользователя (статус 'Создание').
    Объект, возвращаемый этой функцией, также будет "истекшим", если используется
    после закрытия сессии. Если это проблема, здесь тоже можно применить expire_on_commit=False
    или перезагружать объект в вызывающем коде. Для текущего main это не критично,
    т.к. он сразу используется или создается новый.
    """
    async with async_session_() as session:  # Можно оставить по умолчанию, если осторожно использовать
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
        # Если объект будет использоваться сразу после этого вызова и сессия закроется,
        # он также может стать "expired". Для чтения можно также использовать expire_on_commit=False.
        # Либо, если далее объект будет модифицироваться, лучше перезагрузить его в новой сессии.
        active_request = await session.scalar(stmt)
        if active_request:
            # Чтобы быть уверенным, что все атрибуты доступны после закрытия сессии,
            # можно применить тот же паттерн с expire_on_commit=False,
            # или перезагрузить объект.
            # Для простоты оставим так, но если будут ошибки, применить expire_on_commit=False.
            # Либо, если мы ТОЧНО знаем, что все нужные поля уже загружены (не deferred),
            # и мы не будем их модифицировать без новой сессии, то может быть ОК.
            # Для большей надежности, если объект передается дальше:
            # session.refresh(active_request) # Убедиться, что все загружено
            # session.expunge(active_request) # Отсоединить
            pass  # просто для примера, что здесь можно что-то сделать
        return active_request


async def update_exchange_request_data(request_id: int, **kwargs) -> ExchangeHistoryTable | None:
    """
    Обновляет данные указанной заявки.
    Возвращенный объект будет доступен для чтения атрибутов после закрытия сессии.
    """
    # Используем expire_on_commit=False для этой конкретной сессии
    async with async_session_(expire_on_commit=False) as session:
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

            print(f"Exchange request {request_id} updated with {kwargs}")
            # Так как expire_on_commit=False, request_to_update не будет "истекшим"
            return request_to_update


async def get_exchange_request_by_id(request_id: int) -> ExchangeHistoryTable | None:
    """Получает заявку по её ID."""
    # Если объект будет использоваться сразу для чтения, можно использовать expire_on_commit=False
    async with async_session_(expire_on_commit=False) as session:  # Добавлено для консистентности
        stmt = select(ExchangeHistoryTable).where(ExchangeHistoryTable.id == request_id)
        request = await session.scalar(stmt)
        return request


async def get_user_exchange_history(
        tg_id: int, include_creation_status: bool = False
) -> list[ExchangeHistoryTable]:
    """
    Получает историю заявок пользователя.
    Объекты в списке будут доступны для чтения атрибутов.
    """
    # Если объекты будут использоваться сразу для чтения, можно использовать expire_on_commit=False
    async with async_session_(expire_on_commit=False) as session:  # Добавлено для консистентности
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


# --- Пример использования (main) ---
async def main():
    # Для чистоты теста, можно раскомментировать, но ОСТОРОЖНО с данными
    # from src.database.models import engine, Base
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)
    #     await conn.run_sync(Base.metadata.create_all)

    user_tg_id = 123456789
    username = "testuser_main_run"
    await set_user(tg_id=user_tg_id, username=username)
    user_role = await get_user_role(tg_id=user_tg_id)
    print(f"User Role: {user_role.value if user_role else 'Not found'}")

    active_req = await get_active_exchange_request(tg_id=user_tg_id)
    if active_req:
        print(f"Found active request: ID {active_req.id}, Status {active_req.status.value}")
    else:
        print("No active request found. Creating a new one...")
        active_req = await create_exchange_request(
            tg_id=user_tg_id,
            currency_from="BTC",
            currency_to="USD",
            give=0.0,
            rate="N/A",
            get=0.0
        )
        if active_req:
            print(f"Created new active request: ID {active_req.id}, Status {active_req.status.value}")

    if active_req:
        print(f"\nUpdating active request {active_req.id}...")
        updated_req = await update_exchange_request_data(
            request_id=active_req.id,
            give=0.5,
            currency_from="BTC_updated",
            rate="50000"
        )
        if updated_req:
            calculated_get = updated_req.give * float(updated_req.rate) if updated_req.rate != "N/A" else 0.0
            final_updated_req = await update_exchange_request_data(  # Присваиваем результат переменной
                request_id=updated_req.id,
                get=calculated_get
            )
            if final_updated_req:  # Проверяем, что final_updated_req не None
                print(
                    f"Updated request {final_updated_req.id}: Give={final_updated_req.give}, Get={final_updated_req.get}, Rate={final_updated_req.rate}")
                active_req = final_updated_req  # Обновляем active_req последней версией

        if active_req:  # Проверяем active_req снова, т.к. он мог быть обновлен
            print(f"\nChanging status of request {active_req.id} to 'Pending Payment'...")
            finalized_req = await update_exchange_request_data(
                request_id=active_req.id,
                status=Status.pending_payment
            )
            if finalized_req:
                print(f"Request {finalized_req.id} status is now: {finalized_req.status.value}")

    print("\nUser exchange history (excluding 'creation'):")
    history = await get_user_exchange_history(tg_id=user_tg_id)
    if not history:
        print("No history found.")
    for item in history:
        print(
            f"  ID: {item.id}, Status: {item.status.value}, From: {item.give} {item.currency_from} "
            f"To: {item.get} {item.currency_to}, Rate: {item.rate}, Date: {item.date}"
        )

    # Создадим еще одну заявку для теста полной истории
    # Используем другой tg_id или убедимся, что предыдущая заявка не 'creation'
    # Если предыдущая заявка стала 'pending_payment', то get_active_exchange_request вернет None для user_tg_id
    # и эта создастся.
    # Если хотим еще одну 'creation' для того же юзера, это нормально, get_active_exchange_request вернет последнюю.
    await create_exchange_request(
        tg_id=user_tg_id, currency_from="ETH", currency_to="USDT",
        give=1.0, rate="2000", get=2000.0
    )

    print("\nUser exchange history (including 'creation'):")
    full_history = await get_user_exchange_history(tg_id=user_tg_id, include_creation_status=True)
    if not full_history:
        print("No history found.")
    for item in full_history:
        print(
            f"  ID: {item.id}, Status: {item.status.value}, From: {item.give} {item.currency_from} "
            f"To: {item.get} {item.currency_to}, Rate: {item.rate}, Date: {item.date}"
        )

    if full_history:
        first_req_id = full_history[0].id
        print(f"\nGetting request by ID: {first_req_id}")
        specific_request = await get_exchange_request_by_id(first_req_id)
        if specific_request:
            print(f"  Found: ID {specific_request.id}, Status {specific_request.status.value}")
        else:
            print(f"  Request with ID {first_req_id} not found.")


if __name__ == "__main__":
    asyncio.run(main())