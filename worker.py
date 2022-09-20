import math
import asyncio
from hashlib import md5
from datetime import datetime

import httpx
from loguru import logger
from pydantic import ValidationError
from googleapiclient import errors

from src.utils import get_logger, get_service
from src.schema import Event as ResponseEvent, Response
from src.models import Event, Calendar
from src.settings import settings
from src.crud.student import get_students_with_calendars
from src.crud.event import create_event, update_event, get_event
from src.crud.calendar import create_calendar, update_calendar, delete_calendar, get_calendar


logger.remove()
logger = get_logger('worker')
EVENTS_COOLDOWN = 0.1
STUDENTS_COOLDOWN = 5
LOOPS_COOLDOWN = 10
ERROR_COOLDOWN = 10


def error_log(e: Exception, text, trace=False):
    if trace:
        logger.exception(f'[{e}/{type(e)}]: {text}')
    else:
        logger.error(f'[{e}/{type(e)}]: {text}')


def get(url: str, max_tries: int = 0) -> Response:
    for _ in range(max_tries):
        try:
            return Response(**httpx.get(url, timeout=10).json())
        except httpx.TimeoutException as e:
            error_log(e, '[Timeout] retrying...')
        except httpx.ConnectError as e:
            error_log(e, '[Connection Error] retrying...')
        except ValueError as e:
            error_log(e, '[503 Service Temporarily Unavailable - ValueError], retrying...')
        except TypeError as e:
            error_log(e, '[503 Service Temporarily Unavailable - TypeError], retrying...')
        raise TimeoutError(f'After {max_tries} tries on {url}, server still can\'t send response')


def get_calendar_from_site(student_id: int) -> list[ResponseEvent] | None:
    try:  # TODO year: 2022-2023
        responses = [
            get(f'{settings.GET_CALENDAR_URL}educationSpaceID=1&showAll=true', max_tries=3)
        ] if student_id == 200000 else [
            # get(f'{settings.GET_CALENDAR_URL}studentID={student_id}&year=2020-2021', max_tries=3),
            # get(f'{settings.GET_CALENDAR_URL}studentID={student_id}&year=2021-2022', max_tries=3),
            get(f'{settings.GET_CALENDAR_URL}studentID={student_id}', max_tries=3)
        ]
        events_list = []
        for response in responses:
            if response.state == 1:
                events_list.extend(response.data.raspList)
            else:
                raise ValueError(f"Error state: {response.state=}; {response.data=}; {response.msg=}")
        if student_id == 200000:
            events_list = [event for event in events_list if event.info.categoryID in [2, 3]]
        logger.info(f'Total - {len(events_list):4d}')
        if not events_list:
            raise ValueError('Site returned no data')
        return events_list
    except TimeoutError as e:
        error_log(e, '[TimeoutError]')
    except ValidationError as e:
        error_log(e, '[ValidationError]')
    except ValueError as e:
        error_log(e, '[503 Service Temporarily Unavailable - ValueError], retrying...')
    except Exception as e:
        error_log(e, '[UNKNOWN ERROR IN REQUESTER]', True)


def cut_event(raw_event: ResponseEvent):
    info_dict = raw_event.info
    if not raw_event.end:
        # All day event (probably - free day), skipping...
        return
    event_ids = raw_event.raspItemsIDs
    event_id = sum(event_ids) if len(event_ids) > 1 else event_ids[0]  # sum may have troubles
    teachers = ', '.join(sorted([teacher.name for teacher in info_dict.teachers]))
    groups = ', '.join(sorted([group.name for group in info_dict.groups]))
    event = Event(
        id=event_id,
        name=raw_event.name,
        color=raw_event.color or '#f0f0f0',
        start=raw_event.start,
        end=raw_event.end,
        aud=info_dict.aud or '',
        link=info_dict.link,
        group_names=groups,
        description=f'Преподаватели: {teachers}\n'
                    f'Модуль: {info_dict.moduleName}\n'
                    f'Тема: {info_dict.theme}\n'
                    f'Группы: {groups}',
    )
    if event.link:
        event.description = f'{event.link}\n{event.description}'
    event.hash = hash_event(event)
    return event


def hash_event(event: Event):
    start = datetime.strftime(event.start.astimezone(), '%Y-%m-%dT%H:%M:%S%z')
    end = datetime.strftime(event.end.astimezone(), '%Y-%m-%dT%H:%M:%S%z')
    if start[-3:-2] != ':':
        start = f'{start[:-2]}:{start[-2:]}'
    if end[-3:-2] != ':':
        end = f'{end[:-2]}:{end[-2:]}'
    return md5(str(
        start + end + event.name +
        event.description + event.aud + event.color
    ).encode('UTF-8')).hexdigest()


def color_picker(input_color):
    def distance(c1, c2):
        (r1, g1, b1) = c1
        (r2, g2, b2) = c2
        return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)

    input_color = (int(input_color[:2], 16), int(input_color[2:4], 16), int(input_color[4:], 16))
    google_colors = {
        (164, 189, 252): '1',
        (122, 231, 191): '2',
        (219, 173, 255): '3',
        (255, 136, 124): '4',
        (251, 215, 91): '5',
        (255, 184, 120): '6',
        (70, 214, 219): '7',
        (225, 225, 225): '8',
        (84, 132, 237): '9',
        (81, 183, 73): '10',
        (220, 33, 39): '11'
    }
    colors = list(google_colors.keys())
    closest_colors = sorted(colors, key=lambda color: distance(color, input_color))
    closest_color = closest_colors[0]
    code = google_colors[closest_color]
    return code


async def calendar_executor(student_id):
    try:
        events_to_create = []
        events_to_update = []
        old_calendar_dict = await get_calendar(student_id)
        calendar_from_site = get_calendar_from_site(student_id)
        if calendar_from_site is None:
            return
        for raw_event in calendar_from_site:
            event = cut_event(raw_event)
            if not event:
                # Skip all day event
                continue
            event_from_db = await get_event(event.id)
            if event_from_db is None:
                await create_event(event)
            elif event_from_db.hash != event.hash:  # elif hash_event(event_from_db) != hash_event(event):
                await update_event(event)
            if event.id not in old_calendar_dict:
                events_to_create.append(event)
            elif old_calendar_dict[event.id] != event.hash:
                events_to_update.append(event)
                old_calendar_dict.pop(event.id)
            else:
                old_calendar_dict.pop(event.id)
        events_to_delete = list(old_calendar_dict)
        if [] == events_to_create == events_to_update == events_to_delete:
            logger.info('Nothing to change')
        else:
            logger.info(f'To create - {len(events_to_create):4d}')
            logger.info(f'To update - {len(events_to_update):4d}')
            logger.info(f'To delete - {len(events_to_delete):4d}')
        return events_to_create, events_to_update, events_to_delete
    except Exception as e:
        error_log(e, '[UNKNOWN ERROR IN CALENDAR EXECUTOR]', True)


async def google_executor(
        service,
        to_google: tuple[list[Event], list[Event], list[int]],
        student_id: int,
        calendar_id: str,
):
    events_to_create, events_to_update, events_to_delete = to_google
    if len(events_to_delete) > 50:
        return logger.info('IT SEEMS THAT CALENDAR DROPPED - REJECTING CHANGES')
    for num, event in enumerate(events_to_create):
        logger.info(f'{num + 1:4d}/{len(events_to_create):4d} - Create')
        await send_google_event(service, calendar_id, event, True)
        await create_calendar(Calendar(student_id=student_id, event_id=event.id, hash=event.hash))
    for num, event in enumerate(events_to_update):
        logger.info(f'{num + 1:4d}/{len(events_to_update):4d} - Update')
        await send_google_event(service, calendar_id, event)
        await update_calendar(Calendar(student_id=student_id, event_id=event.id, hash=event.hash))
    for num, event_id in enumerate(events_to_delete):
        logger.info(f'{num + 1:4d}/{len(events_to_delete):4d} - Delete')
        await delete_google_event(service, calendar_id, event_id)
        await delete_calendar(student_id, event_id)


async def send_google_event(service, calendar_id, event: Event, create=False):
    while True:
        # Requests speed is slow, so we don't need cooldown here
        # Remake this section when this will be slow point
        await asyncio.sleep(EVENTS_COOLDOWN)
        body = {
            'status': 'confirmed',
            'colorId': color_picker(event.color[1:]),
            'summary': event.name,
            'location': event.aud,
            'description': f'{event.description}',
            'id': event.id,
            'start': {
                'dateTime': event.start.isoformat(),
                'timeZone': 'Europe/Moscow',
            },
            'end': {
                'dateTime': event.end.isoformat(),
                'timeZone': 'Europe/Moscow',
            },
        }
        try:
            if create:
                request = service.events().insert(calendarId=calendar_id, body=body)
            else:
                request = service.events().patch(calendarId=calendar_id, eventId=body['id'], body=body)
            return request.execute()
        except errors.HttpError as e:
            if e.resp.status == 403:
                logger.info('403 ERROR, SLEEPING...')
                await asyncio.sleep(ERROR_COOLDOWN)
            elif not create and e.resp.status == 404:
                logger.info('404 ERROR, CREATING...')
                return service.events().insert(calendarId=calendar_id, body=body).execute()
            elif create and e.resp.status == 409:
                logger.info('409 ERROR, PATCHING...')
                return service.events().patch(calendarId=calendar_id, eventId=body['id'], body=body).execute()
            elif e.resp.status in [500, 503]:
                logger.info(f'{e.resp.status} ERROR SLEEPING...')
                error_log(e, f'[{e.resp.status} / GOOGLE IS DOWN]')
                await asyncio.sleep(ERROR_COOLDOWN)
            else:
                logger.info('XXX ERROR SLEEPING...')
                logger.info(event)
                error_log(e, '[XXX / GOOGLE IS DOWN]')
                await asyncio.sleep(ERROR_COOLDOWN)
                raise e
        except Exception as e:
            error_log(e, '[UNKNOWN ERROR IN EVENT CREATE]', True)
            await asyncio.sleep(ERROR_COOLDOWN)


async def delete_google_event(service, calendar_id, event_id):
    while True:
        await asyncio.sleep(EVENTS_COOLDOWN)
        try:
            request = service.events().patch(calendarId=calendar_id, eventId=event_id, body={'status': 'cancelled'})
            return request.execute()
        except errors.HttpError as e:
            if e.resp.status == 403:
                logger.info('403 ERROR SLEEPING...')
            elif e.resp.status in [500, 503]:
                logger.info(f'{e.resp.status} ERROR SLEEPING...')
                error_log(e, f'[{e.resp.status} / GOOGLE IS DOWN]')
            else:
                logger.info('XXX ERROR SLEEPING...')
                error_log(e, '[XXX / GOOGLE IS DOWN]')
            await asyncio.sleep(ERROR_COOLDOWN)
        except Exception as e:
            error_log(e, '[UNKNOWN ERROR IN EVENT DELETE]', True)
            await asyncio.sleep(ERROR_COOLDOWN)


async def parser():
    logger.info('parser')
    while True:
        try:
            service = get_service()
            calendars = await get_students_with_calendars()
            for num, student in enumerate(calendars):
                logger.info(f'({num + 1}/{len(calendars)}) #{student.id} - {student.fio}')
                to_google = await calendar_executor(student.id)
                if to_google is None:
                    logger.info('Skipping google executor due to error above...')
                else:
                    await google_executor(service, to_google, student.id, student.calendar_id)
                await asyncio.sleep(STUDENTS_COOLDOWN)
            logger.info('Last user, sleeping...')
            await asyncio.sleep(LOOPS_COOLDOWN)
        except Exception as e:
            error_log(e, '[UNKNOWN ERROR IN LOOP]', True)
            await asyncio.sleep(ERROR_COOLDOWN * 6)


if __name__ == '__main__':
    import platform

    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(parser())
