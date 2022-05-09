import csv
import asyncio
import tarfile
from pathlib import Path

from sqlalchemy.future import select

from src.db import async_session
from src.models import Calendar, Event, Student


async def dump_db():
    folder = Path('../../csv')
    folder.mkdir(parents=True, exist_ok=True)
    with tarfile.open(folder / 'dump.tar.xz', 'w:xz') as tar:
        for table in [Calendar, Event, Student]:
            with open(folder / f'{table.__tablename__}.csv', 'w', encoding='UTF-8', newline='') as file:
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
            tar.add(folder / f'{table.__tablename__}.csv')


if __name__ == '__main__':
    import platform

    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(dump_db())
