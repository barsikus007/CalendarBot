import csv
import asyncio
from pathlib import Path

from sqlalchemy.future import select

from models import Calendar, Events, Students
from utils import async_session


async def dump_db():
    Path('csv').mkdir(parents=True, exist_ok=True)
    for table in [Calendar, Events, Students]:
        with open(f'csv/{table.__tablename__}.csv', 'w', encoding='UTF-8') as file:
            out_csv = csv.writer(file)
            async with async_session() as session:
                q = await session.execute(
                    select(table)
                )
                records = q.scalars().all()
                out_csv.writerow([column.name for column in table.__mapper__.columns])
                [
                    out_csv.writerow([getattr(curr, column.name) for column in table.__mapper__.columns])
                    for curr in records
                ]


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(dump_db())
