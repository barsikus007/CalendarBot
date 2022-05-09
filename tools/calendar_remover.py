import asyncio

from googleapiclient import errors

from crud import get_students_with_calendars
from utils import get_logger, get_service
from worker import delete_google_event


logger = get_logger('calendar_remover')


def error_log(e: Exception, text):
    logger.error(f'[{e}/{type(e)}]: {text}')


async def google_executor(service, calendar_id):
    events_to_delete = await get_all_google_events(service, calendar_id)
    for num, event in enumerate(events_to_delete):
        logger.info(f'{num+1}/{len(events_to_delete)} - Delete')
        await delete_google_event(service, calendar_id, event['id'])


async def get_all_google_events(service, calendar_id):
    while True:
        await asyncio.sleep(0.5)
        try:
            google_events = service.events().list(calendarId=calendar_id, maxResults=2500).execute()['items']
            return google_events
        except errors.HttpError as e:
            error_log(e, '[Unknown calendar events error]')
        except Exception as e:
            error_log(e, '[UNKNOWN ERROR IN EVENT CREATE]')
            await asyncio.sleep(10)


async def main():
    try:
        exit('Lock from misclick')
        service = get_service(logger)
        calendars = await get_students_with_calendars()
        for num, student in enumerate(calendars):
            logger.info(f'({num + 1}/{len(calendars)}) #{student.id} - {student.fio}')
            await google_executor(service, student.calendar_id)
            await asyncio.sleep(5)
        logger.info('Last user, exiting...')
    except Exception as e:
        error_log(e, '[UNKNOWN ERROR IN LOOP]')
        await asyncio.sleep(300)


if __name__ == '__main__':
    import platform

    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
