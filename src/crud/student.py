from sqlalchemy import update
from sqlmodel import select

from src.db import async_session
from src.models import Student


async def get_students_with_calendars() -> list[Student]:
    async with async_session() as session:
        return (await session.exec(
            select(Student).where(Student.calendar_id.isnot(None)).order_by(Student.id)
        )).all()


async def get_student_by_fio(fio: str) -> Student:
    async with async_session() as session:
        return (await session.exec(
            select(Student).where(Student.fio == fio)
        )).first()


async def get_student_by_student_id(student_id: int) -> Student:
    async with async_session() as session:
        return (await session.exec(
            select(Student).where(Student.id == student_id)
        )).first()


async def get_student_by_telegram_id(telegram_id: int) -> Student:
    async with async_session() as session:
        return (await session.exec(
            select(Student).where(Student.telegram_id == telegram_id)
        )).first()


async def update_student_tg_id(fio: str, tg_id: int):
    async with async_session() as session:
        (await get_student_by_fio(fio)).telegram_id = tg_id
        await session.commit()


async def set_student_calendar(student_id: int, calendar_id: str):
    async with async_session() as session:
        (await get_student_by_student_id(student_id)).calendar_id = calendar_id
        await session.commit()
