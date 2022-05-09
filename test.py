import asyncio
from pydantic import ValidationError

from src.crud.student import get_students_with_calendars
from src.schema import Event
from worker import get_calendar_from_site


async def validate():
    calendars = await get_students_with_calendars()
    for student in calendars:
        print(student.id)
        rasp: list[dict] = get_calendar_from_site(student.id)
        for e in rasp:
            try:
                Event(**e)
            except ValidationError as ee:
                print(ee)
                print(e)


if __name__ == '__main__':
    import platform

    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(validate())
