import math
import asyncio
from hashlib import md5
from datetime import datetime

import httpx
from googleapiclient import errors

from create_db import check_if_exists, add_data_from_old_db, put_students_from_site, create_or_connect_and_reset
from db import get_calendars, get_event, get_calendar
from db import create_event, create_calendar
from db import update_event, update_calendar
from db import delete_calendar
from utils import get_logger, get_service
from src.settings import settings


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


def get_calendar_from_site(student_id):
    try:  # showAll: true; year: 2021-2022
        response1 = httpx.get(f'{settings.GET_CALENDAR_URL}{student_id}&year=2020-2021', timeout=10)
        response2 = httpx.get(f'{settings.GET_CALENDAR_URL}{student_id}', timeout=10)
        raw_events_list = [*response1.json()['data']['raspList'], *response2.json()['data']['raspList']]
        logger.info(f'Total - {len(raw_events_list)}')
        if len(raw_events_list) == 0:
            raise ValueError('Site returned no data')
        return raw_events_list
    except ValueError as e:
        error_log(e, '[503 Service Temporarily Unavailable - ValueError]')
    except TypeError as e:
        error_log(e, '[503 Service Temporarily Unavailable - TypeError]')
    except httpx.TimeoutException as e:
        error_log(e, '[Timeout]')
    except Exception as e:
        error_log(e, '[UNKNOWN ERROR IN REQUESTER]', True)


def cut_event(raw_event):
    info_dict = raw_event['info']
    if not raw_event['end']:
        # All day event (probably - free day), skipping...
        return
    teachers = ', '.join(sorted([teacher['name'] for teacher in info_dict['teachers']]))
    groups = ', '.join(sorted([group['name'] for group in info_dict['groups']]))
    event = {
        'name': raw_event['name'],
        'color': raw_event['color'] or '#f0f0f0',
        'start': raw_event['start'],
        'end': raw_event['end'],
        'rasp_item_ids': raw_event['raspItemsIDs'],
        'aud': info_dict['aud'] or '',
        'link': info_dict['link'],
        'teacher': teachers,
        'module_name': info_dict['moduleName'],
        'theme': info_dict['theme'],
        'group_name': groups,
        'description': f"Преподаватели: {teachers}\n"
                       f"Модуль: {info_dict['moduleName']}\n"
                       f"Тема: {info_dict['theme']}\n"
                       f"Группы: {groups}",
    }
    if event['link']:
        event['description'] = f"{event['link']}\n{event['description']}"
    return event


def hash_event(event):
    return md5(str(
        event['start'] + event['end'] + event['name'] +
        event['description'] + event['aud'] + event['color']
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
            event['hash'] = hash_event(event)
            event['start'] = datetime.strptime(event['start'], '%Y-%m-%dT%H:%M:%S%z')
            event['end'] = datetime.strptime(event['end'], '%Y-%m-%dT%H:%M:%S%z')
            rasp_item_ids = event.pop('rasp_item_ids')
            if len(rasp_item_ids) > 1:
                event_id = sum(rasp_item_ids)  # May have troubles
            else:
                event_id = rasp_item_ids[0]
            event_from_db = await get_event(event_id)
            event['rasp_item_id'] = event_id
            if event_from_db is None:
                await create_event(event)
            elif event_from_db.hash != event['hash']:
                await update_event(event)
            if event_id not in old_calendar_dict:
                events_to_create.append(event)
            elif old_calendar_dict[event_id] != event['hash']:
                events_to_update.append(event)
                old_calendar_dict.pop(event_id)
            else:
                old_calendar_dict.pop(event_id)
        events_to_delete = [_ for _ in old_calendar_dict]
        if [] == events_to_create == events_to_update == events_to_delete:
            logger.info(f'Nothing to change')
        else:
            logger.info(f'To create - {len(events_to_create)}')
            logger.info(f'To update - {len(events_to_update)}')
            logger.info(f'To delete - {len(events_to_delete)}')
        return events_to_create, events_to_update, events_to_delete
    except Exception as e:
        error_log(e, '[UNKNOWN ERROR IN CALENDAR EXECUTOR]', True)


async def google_executor(service, to_google, student_id, calendar_id):
    events_to_create, events_to_update, events_to_delete = to_google
    if len(events_to_delete) > 50:
        return logger.info('IT SEEMS THAT CALENDAR DROPPED - REJECTING CHANGES')
    for num, event in enumerate(events_to_create):
        logger.info(f'{num+1}/{len(events_to_create)} - Create')
        await send_google_event(service, calendar_id, event, True)
        await create_calendar(student_id, event['rasp_item_id'], event['hash'])
    for num, event in enumerate(events_to_update):
        logger.info(f'{num+1}/{len(events_to_update)} - Update')
        await send_google_event(service, calendar_id, event)
        await update_calendar(student_id, event['rasp_item_id'], event['hash'])
    for num, event_id in enumerate(events_to_delete):
        logger.info(f'{num+1}/{len(events_to_delete)} - Delete')
        await delete_google_event(service, calendar_id, event_id)
        await delete_calendar(student_id, event_id)


async def send_google_event(service, calendar_id, event, create=False):
    while True:
        # Requests speed is slow, so we don't need cooldown here
        # Remake this section when this will be slow point
        await asyncio.sleep(EVENTS_COOLDOWN)
        body = {
            'status': 'confirmed',
            'colorId': color_picker(event['color'][1:]),
            'summary': event["name"],
            'location': event['aud'],
            'description': f'{event["description"]}',
            'id': event['rasp_item_id'],
            'start': {
                'dateTime': event['start'].isoformat(),
                'timeZone': 'Europe/Moscow',
            },
            'end': {
                'dateTime': event['end'].isoformat(),
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
                error_log(e, f'[XXX / GOOGLE IS DOWN]')
                await asyncio.sleep(ERROR_COOLDOWN)
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
                await asyncio.sleep(ERROR_COOLDOWN)
            elif e.resp.status in [500, 503]:
                logger.info(f'{e.resp.status} ERROR SLEEPING...')
                error_log(e, f'[{e.resp.status} / GOOGLE IS DOWN]')
                await asyncio.sleep(ERROR_COOLDOWN)
            else:
                logger.info('XXX ERROR SLEEPING...')
                error_log(e, f'[XXX / GOOGLE IS DOWN]')
                await asyncio.sleep(ERROR_COOLDOWN)
        # except ConnectionResetError as e:
        #     error_log(e, '[WinError ConnectionResetError]')
        # except OSError as e:
        #     error_log(e, '[OSError]')
        except Exception as e:
            error_log(e, '[UNKNOWN ERROR IN EVENT DELETE]', True)
            await asyncio.sleep(ERROR_COOLDOWN)


async def main():
    exists = await check_if_exists()
    logger.info('Database' + (' ' if exists else ' not ') + 'exists!')
    if not exists:
        await create_or_connect_and_reset()
        await put_students_from_site()
        await add_data_from_old_db()
        logger.info('Database created!')
    while True:
        try:
            service = get_service(logger)
            calendars = await get_calendars()
            for num, student in enumerate(calendars):
                logger.info(f'({num + 1}/{len(calendars)}) #{student.student_id} - {student.fio}')
                to_google = await calendar_executor(student.student_id)
                if to_google is None:
                    logger.info(f'Skipping google executor due to error above...')
                else:
                    await google_executor(service, to_google, student.student_id, student.calendar_id)
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
    asyncio.run(main())
