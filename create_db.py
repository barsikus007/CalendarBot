import csv
import asyncio
from datetime import datetime

import requests
from asyncpg.exceptions import ConnectionDoesNotExistError

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config import get_students_url, DB_AUTH
from utils import Base, engine, async_session
from dal import StudentsDAL, EventsDAL, CalendarDAL


async def create_if_not_exists():
    postgres_engine = create_async_engine(
        f'postgresql+asyncpg://{DB_AUTH["user"]}:{DB_AUTH["password"]}@{DB_AUTH["host"]}:{DB_AUTH["port"]}/postgres',
        echo=False
    )
    postgres_async_session = sessionmaker(postgres_engine, expire_on_commit=False, class_=AsyncSession)
    async with postgres_async_session.begin() as session:
        await session.execute('COMMIT')
        await session.execute(f'CREATE DATABASE {DB_AUTH["database"]}')


async def reset():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def create_or_connect_and_reset():
    try:
        await reset()
    except ConnectionDoesNotExistError:
        await create_if_not_exists()
        await reset()


async def put_students_from_site():
    students_list = requests.get(get_students_url).json()['data']['allStudent']
    students_list = [[_['studentID'], _['fullName']] for _ in students_list]
    async with async_session() as session:
        async with session.begin():
            students = StudentsDAL(session)
            await students.create_students(students_list)


async def add_data_from_old_db():
    with open('csv/students.csv', 'r', encoding='UTF-8') as f:
        in_csv = csv.reader(f)
        async with async_session() as session:
            async with session.begin():
                students = StudentsDAL(session)
                for row in in_csv:
                    if in_csv.line_num == 1:
                        continue
                    if not row:
                        continue
                    if not (row[2] or row[3]):
                        continue
                    await students.update_student(
                        student_id=int(row[0]),
                        telegram_id=int(row[2]) if row[2] else None,
                        calendar_id=row[3] if row[3] else None
                    )
    with open('csv/events.csv', 'r', encoding='UTF-8') as f:
        in_csv = csv.reader(f)
        async with async_session() as session:
            async with session.begin():
                events = EventsDAL(session)
                for row in in_csv:
                    if in_csv.line_num == 1:
                        continue
                    if not row:
                        continue
                    await events.create_event(
                        {
                            'rasp_item_id': int(row[0]),
                            'start': datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S%z'),
                            'end': datetime.strptime(row[2], '%Y-%m-%d %H:%M:%S%z'),
                            'name': row[3],
                            'color': row[4] if row[4] else None,
                            'aud': row[5] if row[5] else None,
                            'link': row[6] if row[6] else None,
                            'teacher': row[7] if row[7] else None,
                            'module_name': row[8] if row[8] else None,
                            'theme': row[9] if row[9] else None,
                            'group_name': row[10] if row[10] else None,
                            'description': row[11] if row[11] else None,
                            'hash': row[12] if row[12] else None
                        }
                    )
    with open('csv/calendar.csv', 'r', encoding='UTF-8') as f:
        in_csv = csv.reader(f)
        async with async_session() as session:
            async with session.begin():
                calendar = CalendarDAL(session)
                for row in in_csv:
                    if in_csv.line_num == 1:
                        continue
                    if not row:
                        continue
                    await calendar.create_calendar(
                        student_id=int(row[0]),
                        rasp_item_id=int(row[1]),
                        event_hash=row[2]
                    )


if __name__ == '__main__':
    exit('Locked, use with care!')
    asyncio.get_event_loop().run_until_complete(create_or_connect_and_reset())
    asyncio.get_event_loop().run_until_complete(put_students_from_site())
    asyncio.get_event_loop().run_until_complete(add_data_from_old_db())
