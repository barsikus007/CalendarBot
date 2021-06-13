from dal import StudentsDAL, EventsDAL, CalendarDAL

from utils import async_session


async def get_calendars():
    async with async_session() as session:
        async with session.begin():
            students = StudentsDAL(session)
            return await students.get_calendars()


async def get_event(rasp_item_id: int):
    async with async_session() as session:
        async with session.begin():
            events = EventsDAL(session)
            return await events.get_event_by_id(rasp_item_id)


async def create_event(event: dict):
    async with async_session() as session:
        async with session.begin():
            events = EventsDAL(session)
            await events.create_event(event)


async def update_event(event: dict):
    async with async_session() as session:
        async with session.begin():
            events = EventsDAL(session)
            return await events.update_event(event)


async def get_calendar(student_id: int):
    async with async_session() as session:
        async with session.begin():
            calendar = CalendarDAL(session)
            return {_.rasp_item_id: _.hash for _ in await calendar.get_calendar(student_id)}


async def create_calendar(student_id: int, rasp_item_id: int, event_hash: str):
    async with async_session() as session:
        async with session.begin():
            calendar = CalendarDAL(session)
            await calendar.create_calendar(student_id, rasp_item_id, event_hash)


async def update_calendar(student_id: int, rasp_item_id: int, event_hash: str):
    async with async_session() as session:
        async with session.begin():
            calendar = CalendarDAL(session)
            await calendar.update_calendar(student_id, rasp_item_id, event_hash)


async def delete_calendar(student_id: int, rasp_item_id: int):
    async with async_session() as session:
        async with session.begin():
            calendar = CalendarDAL(session)
            await calendar.delete_calendar(student_id, rasp_item_id)


async def get_student_by_fio(fio: str):
    async with async_session() as session:
        async with session.begin():
            students = StudentsDAL(session)
            return await students.get_student_by_fio(fio)


async def get_student_by_telegram_id(telegram_id: int):
    async with async_session() as session:
        async with session.begin():
            students = StudentsDAL(session)
            return await students.get_student_by_telegram_id(telegram_id)


async def update_student_tg_id(fio: str, tg_id: int):
    async with async_session() as session:
        async with session.begin():
            students = StudentsDAL(session)
            return await students.set_student_tg_id(fio, tg_id)


async def set_student_calendar(student_id: int, calendar_id: str):
    async with async_session() as session:
        async with session.begin():
            students = StudentsDAL(session)
            return await students.set_student_calendar(student_id, calendar_id)
