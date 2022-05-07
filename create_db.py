import csv
import asyncio
from datetime import datetime

import httpx
from asyncpg.exceptions import ConnectionDoesNotExistError

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.settings import settings
from utils import Base, engine, async_session
from dal import StudentsDAL, EventsDAL, CalendarDAL


async def create_if_not_exists():
    postgres_engine = create_async_engine(
        settings.DATABASE_URL.rsplit('/', 1)[0] + '/postgres',
        echo=False
    )
    postgres_async_session = sessionmaker(postgres_engine, expire_on_commit=False, class_=AsyncSession)
    async with postgres_async_session.begin() as session:
        await session.execute('COMMIT')
        await session.execute(f'CREATE DATABASE {settings.POSTGRES_DB}')


async def reset():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def check_if_exists():
    try:
        async with engine.begin() as conn:
            return await conn.run_sync(lambda _: inspect(_).has_table('calendar'))
    except Exception as e:
        print(e)
        print(type(e))
        print('EXCEPTION')
        return True


async def create_or_connect_and_reset():
    try:
        await reset()
    except ConnectionDoesNotExistError:
        await create_if_not_exists()
        await reset()


async def put_students_from_site():
    students_list = httpx.get(settings.GET_STUDENTS_URL).json()['data']['allStudent']
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


async def main():
    exists = await check_if_exists()
    if not exists:
        await create_or_connect_and_reset()
        await put_students_from_site()
        await add_data_from_old_db()


if __name__ == '__main__':
    import platform

    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
