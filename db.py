import asyncio

from sqlalchemy import text, func
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base, relationship, selectinload, sessionmaker

from models import Students, Events, Calendar
from dal import StudentsDAL, EventsDAL, CalendarDAL

from config import engine, async_session


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
