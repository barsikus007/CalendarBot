import asyncio

from sqlalchemy import text, func
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base, relationship, selectinload, sessionmaker

from models import Students, Events, Calendar
from dal import StudentsDAL, EventsDAL, CalendarDAL

from config import engine, async_session


'''class A(Base):
    __tablename__ = "a"

    id = Column(Integer, primary_key=True)
    data = Column(String)
    create_date = Column(DateTime, server_default=func.now())
    bs = relationship("B")

    # required in order to access columns with server defaults
    # or SQL expression defaults, subsequent to a flush, without
    # triggering an expired load
    __mapper_args__ = {"eager_defaults": True}


class B(Base):
    __tablename__ = "b"
    id = Column(Integer, primary_key=True)
    a_id = Column(ForeignKey("a.id"))
    data = Column(String)'''


'''async def async_main():
    async with async_session() as session:
        async with session.begin():
            session.add_all(
                [
                    A(bs=[B(), B()], data="a1"),
                    A(bs=[B()], data="a2"),
                    A(bs=[B(), B()], data="a3"),
                ]
            )

        stmt = select(A).options(selectinload(A.bs))

        result = await session.execute(stmt)

        for a1 in result.scalars():
            print(a1)
            print(f"created at: {a1.create_date}")
            for b1 in a1.bs:
                print(b1)

        result = await session.execute(select(A).order_by(A.id))

        a1 = result.scalars().first()

        a1.data = "new data"

        await session.commit()

        # access attribute subsequent to commit; this is what
        # expire_on_commit=False allows
        print(a1.data)'''


async def conn_example():
    async with engine.begin() as conn:
        result = await conn.execute(
            text('SELECT * FROM students WHERE student_id=271213')
        )
        for row in result:
            print("username:", row['fio'])


async def get_calendars():
    async with async_session() as session:
        async with session.begin():
            students = StudentsDAL(session)
            return await students.get_calendars()


async def get_event(rasp_item_id: int):
    async with async_session() as session:
        async with session.begin():
            events = EventsDAL(session)
            return await events.get_event_by_id(rasp_item_id)


async def create_event(event: dict):
    async with async_session() as session:
        async with session.begin():
            events = EventsDAL(session)
            await events.create_event(event)


async def update_event(event: dict):
    async with async_session() as session:
        async with session.begin():
            events = EventsDAL(session)
            return await events.update_event(event)


async def get_calendar(student_id: int):
    async with async_session() as session:
        async with session.begin():
            calendar = CalendarDAL(session)
            return {_.rasp_item_id: _.hash for _ in await calendar.get_calendar(student_id)}


async def create_calendar(student_id: int, rasp_item_id: int, event_hash: str):
    async with async_session() as session:
        async with session.begin():
            calendar = CalendarDAL(session)
            await calendar.create_calendar(student_id, rasp_item_id, event_hash)


async def update_calendar(student_id: int, rasp_item_id: int, event_hash: str):
    async with async_session() as session:
        async with session.begin():
            calendar = CalendarDAL(session)
            await calendar.update_calendar(student_id, rasp_item_id, event_hash)


async def delete_calendar(student_id: int, rasp_item_id: int):
    async with async_session() as session:
        async with session.begin():
            calendar = CalendarDAL(session)
            await calendar.delete_calendar(student_id, rasp_item_id)


if __name__ == '__main__':
    # asyncio.get_event_loop().run_until_complete(conn_example())
    # asyncio.run(async_main())
    pass
