import csv
import asyncio
from datetime import datetime
from pathlib import Path

from src.db import async_session
from src.models import Calendar, Event, Student


def get_students(folder):
    with open(folder / 'students.csv', 'r', encoding='UTF-8') as f:
        reader = csv.reader(f)
        return [
            Student(
                id=int(row[0]),
                fio=row[1],
                telegram_id=int(row[2]) if row[2] else None,
                calendar_id=row[3] or None,
            ) for row in reader if reader.line_num != 1
        ]


def get_events(folder):
    with open(folder / 'events.csv', 'r', encoding='UTF-8') as f:
        reader = csv.reader(f)
        return [
            Event(
                id=int(row[0]),
                name=row[3],
                color=row[4],
                start=datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S%z'),
                end=datetime.strptime(row[2], '%Y-%m-%d %H:%M:%S%z'),
                aud=row[5] or None,
                link=row[6] or None,
                teachers=row[7] or None,
                module_name=row[8],
                theme=row[9],
                group_names=row[10],
                description=row[11],
                hash=row[12],
            ) for row in reader if reader.line_num != 1
        ]


def get_calendars(folder):
    with open(folder / 'calendar.csv', 'r', encoding='UTF-8') as f:
        reader = csv.reader(f)
        return [
            Calendar(
                student_id=int(row[0]),
                event_id=int(row[1]),
                hash=row[2],
            ) for row in reader if reader.line_num != 1
        ]


def import_dump_for_alembic():
    folder = Path('../../csv')
    students = get_students(folder)
    events = get_events(folder)
    calendars = get_calendars(folder)
    return (
        [_.dict() for _ in students],
        [_.dict() for _ in events],
        [_.dict() for _ in calendars]
    )


async def import_dump():
    folder = Path('../../csv')
    students = get_students(folder)
    events = get_events(folder)
    calendars = get_calendars(folder)
    async with async_session() as session:
        [session.add(_) for _ in students]
        [session.add(_) for _ in events]
        await session.commit()
        [session.add(_) for _ in calendars]
        await session.commit()


if __name__ == '__main__':
    import platform

    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(import_dump())
