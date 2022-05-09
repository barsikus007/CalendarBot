from sqlalchemy import update, delete
from sqlmodel import select

from src.db import async_session
from src.models import Calendar


async def get_calendar(student_id: int) -> dict[int, str]:
    async with async_session() as session:
        calendars = (
            await session.exec(
                select(Calendar).where(Calendar.student_id == student_id)
            )
        ).all()
        return {_.event_id: _.hash for _ in calendars}


async def create_calendar(calendar: Calendar):
    async with async_session() as session:
        session.add(calendar)
        await session.commit()


async def update_calendar(calendar: Calendar):
    async with async_session() as session:
        q = update(Calendar).where(
            Calendar.student_id == calendar.student_id, Calendar.event_id == calendar.event_id
        )
        q = q.values(hash=calendar.hash).execution_options(synchronize_session="fetch")
        await session.exec(q)
        await session.commit()


async def delete_calendar(student_id: int, event_id: int):
    async with async_session() as session:
        await session.exec(
            delete(Calendar).where(
                Calendar.student_id == student_id, Calendar.event_id == event_id
            )
        )
        await session.commit()
