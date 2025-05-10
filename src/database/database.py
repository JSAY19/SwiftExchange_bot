from src.database.models import async_session_, UserTable, ExchangeHistoryTable, Role
from sqlalchemy import select, delete
import asyncio

async def set_user(tg_id: int, username: str = None):
    """Запись юзера в бд"""
    async with async_session_() as session:
        stmt = select(UserTable).where(UserTable.tg_id == tg_id)
        user = await session.scalar(stmt)

        if not user:
            user = UserTable(tg_id=tg_id, role=Role.client, username=username)
            session.add(user)
            await session.commit()

        if user and user.username != username:
            user.username = username
            await session.commit()


async def get_user_role(tg_id: int):
    """Получение роли юзера, для открытия профиля"""
    async with async_session_() as session:
        stmt = select(UserTable).where(UserTable.tg_id == tg_id)
        user = await session.scalar(stmt)
        return user.role.value # получишь роль юзера


#async def set_exchange_user_history()


# async def get_exchange_user_history(tg_id:int):
#     async with async_session_() as session:
#         data = await session.execute(
#             select(UserTable, ExchangeHistoryTable)
#             .join(ExchangeHistoryTable, ExchangeHistoryTable.user_id == UserTable.id)
#             .where(UserTable.tg_id == tg_id)
#         )
#
#         if data:
#             return data
#         else:
#             return None


async def main():
    #await set_user(tg_id=1001, username='@merfohacevv')
    user_role = await get_user_role(tg_id=1001)
    print(type(user_role))

if __name__ == '__main__':
    asyncio.run(main())

