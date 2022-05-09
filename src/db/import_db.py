import csv
import asyncio
from pathlib import Path

from src.db import async_session
from src.models import Calendar, Event, Student


def get_students(folder):
    with open(folder / 'student.csv', 'r', encoding='UTF-8') as f:
        reader = csv.DictReader(f)
        return [
            Student.parse_obj(row) for row in reader
        ]


def get_events(folder):
    with open(folder / 'event.csv', 'r', encoding='UTF-8') as f:
        reader = csv.DictReader(f)
        return [
            Event.parse_obj(row) for row in reader
        ]


def get_calendars(folder):
    with open(folder / 'calendar.csv', 'r', encoding='UTF-8') as f:
        reader = csv.DictReader(f)
        return [
            Calendar.parse_obj(row) for row in reader
        ]


def import_dump_for_alembic():
    folder = Path('csv')
    students = get_students(folder)
    events = get_events(folder)
    calendars = get_calendars(folder)
    return (
        [_.dict() for _ in students if _.telegram_id and _.calendar_id],
        [_.dict() for _ in students if not(_.telegram_id and _.calendar_id)],
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
