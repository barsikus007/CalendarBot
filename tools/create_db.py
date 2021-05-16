import pickle
import asyncio

import httpx

from config import get_students_url
from utils import Base, engine, async_session
from dal import StudentsDAL


async def reset():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def put_students_from_site():
    students_list = httpx.get(get_students_url).json()['data']['allStudent']
    students_list = [[_['studentID'], _['fullName']] for _ in students_list]
    async with async_session() as session:
        async with session.begin():
            students = StudentsDAL(session)
            await students.create_students(students_list)


async def add_data_from_old_db():
    with open('../calendars.pickle', 'rb') as f:
        calendars = pickle.load(f)
    with open('../database.pickle', 'rb') as f:
        database = pickle.load(f)
    async with async_session() as session:
        async with session.begin():
            students = StudentsDAL(session)
            for cal in calendars:
                await students.update_student(student_id=cal, calendar_id=calendars[cal])
            for cal in database:
                await students.update_student(student_id=database[cal]['uid'], telegram_id=cal)


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(reset())
    asyncio.get_event_loop().run_until_complete(put_students_from_site())
    asyncio.get_event_loop().run_until_complete(add_data_from_old_db())
