import asyncio

import httpx
import asyncpg

from config import DB_AUTH, get_students
from DbWorker import AIODb


async def connect_or_create(args):
    try:
        conn = await asyncpg.connect(**args)
    except asyncpg.exceptions.ConnectionDoesNotExistError or asyncpg.InvalidCatalogNameError:
        sys_conn = await asyncpg.connect(
            database='template1',
            user=args['user'],
            host=args['host'],
            port=args['port'],
            password=args['password'],
        )
        user = args['user']
        database = args['database']
        await sys_conn.execute(
            f'CREATE DATABASE "{database}" OWNER "{user}"'
        )
        await sys_conn.close()
        conn = await asyncpg.connect(**args)
    return conn


async def create_tables(conn):
    await conn.execute(f'''
create table students
(
    id          serial not null
        constraint students_pk
            primary key,
    fio         text   not null,
    calendar_id text,
    telegram_id integer
);

alter table students
    owner to postgres;
''')
    await conn.execute(f'''
create table events
(
    rasp_item_id serial                   not null
        constraint events_pk
            primary key,
    start        timestamp with time zone not null,
    "end"        timestamp with time zone,
    name         text                     not null,
    color        text,
    teacher      text,
    module_name  text,
    theme        text,
    group_name   text,
    description  text,
    aud          text,
    link         text
);

alter table events
    owner to postgres;

create unique index events_rasp_item_id_uindex
    on events (rasp_item_id);
''')
    await conn.execute(f'''
create table calendar
(
    student_id   integer
        constraint calendar_students_id_fk
            references students,
    rasp_item_id integer
        constraint calendar_events_rasp_item_id_fk
            references events
);

alter table calendar
    owner to postgres;
''')


async def students():
    students_list = httpx.get(get_students).json()['data']['allStudent']

    adb = AIODb(DB_AUTH)
    sql_list = []
    for student in students_list:
        uid = student['studentID']
        fio = student['fullName']
        if len(fio.split()) != 3:
            print(f'Student {uid} - {fio} have error in their name\nFix it manually!')
        sql_list.append(('INSERT INTO calendar.public.students(id, fio) VALUES ($1, $2)', [uid, fio]))
    await adb.sql.mass_query(sql_list)


# async def posts():
#     db = Db()
#     adb = AIODb(DB_AUTH)
#     sql_list = []
#     db.reopen()
#     for post in db.sql.query_fetch('SELECT * FROM posts'):
#         print(post)
#         sql_list.append(('INSERT INTO posts('
#                          'id, json, current, post_at, from_id, date,'
#                          'post_id, first_current, upvotes, downvotes, can_vote)'
#                          'VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)', post))
#     await adb.sql.mass_query(sql_list)


async def main():
    conn = await connect_or_create(DB_AUTH)
    # await create_tables(conn)
    await students()


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
