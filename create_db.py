import csv
import pickle
import asyncio

import asyncpg
import requests
import sqlalchemy

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from config import get_students_url, DB_AUTH
from utils import Base, engine, async_session
from dal import StudentsDAL, EventsDAL, CalendarDAL


async def connect_or_create():
    import csv
    engine2 = create_async_engine(f'postgresql+asyncpg://{DB_AUTH["user"]}:{DB_AUTH["password"]}@{DB_AUTH["host"]}:{DB_AUTH["port"]}/test', echo=False)
    async_session2 = sessionmaker(engine2, expire_on_commit=False, class_=AsyncSession)

    async with engine2.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    students_list = requests.get(get_students_url).json()['data']['allStudent']
    students_list = [[_['studentID'], _['fullName']] for _ in students_list]
    async with async_session2() as session:
        async with session.begin():
            students = StudentsDAL(session)
            await students.create_students(students_list)
    with open('csv/students.csv', 'r', encoding='UTF-8') as f:
        in_csv = csv.reader(f)
        async with async_session2() as session:
            async with session.begin():
                students = StudentsDAL(session)
                for row in in_csv:
                    if in_csv.line_num == 1:
                        continue
                    if not row:
                        continue
                    if not(row[2] or row[3]):
                        continue
                    if row[2]:
                        tg_id = int(row[2])
                    else:
                        tg_id = None
                    if row[3]:
                        cal_id = row[3]
                    else:
                        cal_id = None
                    await students.update_student(student_id=int(row[0]), telegram_id=tg_id, calendar_id=cal_id)
    with open('csv/events.csv', 'r', encoding='UTF-8') as f:
        in_csv = csv.reader(f)
        async with async_session2() as session:
            async with session.begin():
                events = EventsDAL(session)
                for row in in_csv:
                    if in_csv.line_num == 1:
                        continue
                    if not row:
                        continue
                    print(row)
                    continue
                    if not(row[2] or row[3]):
                        continue
                    if row[2]:
                        tg_id = int(row[2])
                    else:
                        tg_id = None
                    if row[3]:
                        cal_id = row[3]
                    else:
                        cal_id = None
                    await events.update_student(student_id=int(row[0]), telegram_id=tg_id, calendar_id=cal_id)
    exit()
    with open('csv/calendar.csv', 'r', encoding='UTF-8') as f:
        in_csv = csv.reader(f)
        async with async_session2() as session:
            async with session.begin():
                calendar = CalendarDAL(session)
                for row in in_csv:
                    if in_csv.line_num == 1:
                        continue
                    if not row:
                        continue
                    print(row)
                    continue
                    if not(row[2] or row[3]):
                        continue
                    if row[2]:
                        tg_id = int(row[2])
                    else:
                        tg_id = None
                    if row[3]:
                        cal_id = row[3]
                    else:
                        cal_id = None
                    await students.update_student(student_id=int(row[0]), telegram_id=tg_id, calendar_id=cal_id)
    exit()
    try:
        conn = await asyncpg.connect(**DB_AUTH)
    except (asyncpg.exceptions.ConnectionDoesNotExistError, asyncpg.InvalidCatalogNameError):
        sys_conn = await asyncpg.connect(
            database='template1',
            user=DB_AUTH['user'],
            host=DB_AUTH['host'],
            port=DB_AUTH['port'],
            password=DB_AUTH['password'],
        )
        user = DB_AUTH['user']
        database = DB_AUTH['database']
        await sys_conn.execute(
            f'CREATE DATABASE "{database}" OWNER "{user}"'
        )
        await sys_conn.close()
        conn = await asyncpg.connect(**DB_AUTH)
    return conn


async def reset():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def put_students_from_site():
    students_list = requests.get(get_students_url).json()['data']['allStudent']
    students_list = [[_['studentID'], _['fullName']] for _ in students_list]
    async with async_session() as session:
        async with session.begin():
            students = StudentsDAL(session)
            await students.create_students(students_list)


async def add_data_from_old_db():
    exit('TODO csv')
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
                    if not(row[2] or row[3]):
                        continue
                    if row[2]:
                        tg_id = int(row[2])
                    else:
                        tg_id = None
                    if row[3]:
                        cal_id = row[3]
                    else:
                        cal_id = None
                    await students.update_student(student_id=int(row[0]), telegram_id=tg_id, calendar_id=cal_id)


if __name__ == '__main__':
    exit('Locked, use with care!')
    asyncio.get_event_loop().run_until_complete(connect_or_create())
    asyncio.get_event_loop().run_until_complete(reset())
    asyncio.get_event_loop().run_until_complete(put_students_from_site())
    asyncio.get_event_loop().run_until_complete(add_data_from_old_db())
