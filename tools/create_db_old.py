import asyncio

import asyncpg

from config import DB_AUTH


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


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(connect_or_create(DB_AUTH))
