import time
import ujson as json

from connections import POSTGRES

from config import DB_AUTH


class AIODb:
    def __init__(self, auth=None):
        if auth is None:
            self.auth = DB_AUTH
        else:
            self.auth = auth
        self.sql = POSTGRES(self.auth)

    async def user_exists(self, uid):
        return await self.sql.query_fetch('SELECT * FROM users WHERE id=$1', [uid])

    async def add_user(self, uid):
        await self.sql.query('INSERT INTO users(id, date) VALUES ($1, $2)', [uid, int(time.time())])

    async def get_user(self, uid):
        res = await self.sql.query_fetch('SELECT * FROM users WHERE id=$1', [int(uid)])
        return res[0] if res else None

    async def change_status(self, uid, status):
        await self.sql.query('UPDATE users SET dialog_status=$1 WHERE id=$2', [status, uid])

    async def change_param(self, uid, param, value):
        await self.sql.query(f'UPDATE users SET {param}=$1 WHERE id=$2', [value, uid])

    async def add_post(self, j, uid):
        await self.sql.query(
            'INSERT INTO posts(json, from_id) VALUES ($1, $2)', [json.dumps(j, ensure_ascii=False), uid])

    async def delete_post(self, pid=None, first=False):
        if not pid and not first:
            post = await self.sql.query_fetch('SELECT * FROM posts WHERE current=1')
            pid = post[0][0]
        elif not pid and first:
            post = await self.sql.query_fetch('SELECT * FROM posts WHERE first_current=1')
            pid = post[0][0]
        await self.sql.query('DELETE FROM posts WHERE id=$1', [pid])
