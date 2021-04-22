import asyncio

import asyncpg


class POSTGRES:
    def __init__(self, auth):
        self.auth = auth
        self.conn = None

    def sql_pg(self, query: str):
        do = query.find('?')
        i = 1
        if do == -1:
            do = 0
        while do:
            query = f'{query[:do]}${i}{query[do + 1:]}'
            i += 1
            do = query.find('?')
            if do < 0:
                do = 0
        return query

    async def create_connection(self):
        if self.conn is None:
            self.conn = await asyncpg.connect(**self.auth)
        return self.conn

    async def query_fetch(self, sql, parameters=None):
        conn = await self.create_connection()
        sql = self.sql_pg(sql)
        while True:
            try:
                if parameters is None:
                    ret = [list(_) for _ in await conn.fetch(sql)]
                    return ret
                else:
                    ret = [list(_) for _ in await conn.fetch(sql, *parameters)]
                    return ret
            except Exception as e:
                if 'another operation is in progress' in str(e):
                    await asyncio.sleep(1)
                else:
                    raise e

    async def mass_query_fetch(self, sql_list):
        async with asyncpg.create_pool(**self.auth) as pool:
            async with pool.acquire() as con:
                for sql, parameters in sql_list:
                    sql = self.sql_pg(sql)
                    if parameters is None:
                        await con.fetch(sql)
                    else:
                        await con.fetch(sql, *parameters)

    async def query(self, sql, parameters=None):
        conn = await self.create_connection()
        sql = self.sql_pg(sql)
        while True:
            try:
                if parameters is None:
                    ret = await conn.execute(sql)
                    return ret
                else:
                    ret = await conn.execute(sql, *parameters)
                    return ret
            except Exception as e:
                if 'another operation is in progress' in str(e):
                    await asyncio.sleep(1)
                else:
                    raise e

    async def mass_query(self, sql_list):
        async with asyncpg.create_pool(**self.auth) as pool:
            async with pool.acquire() as con:
                for sql, parameters in sql_list:
                    sql = self.sql_pg(sql)
                    if parameters is None:
                        await con.execute(sql)
                    else:
                        await con.execute(sql, *parameters)
