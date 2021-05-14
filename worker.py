import time
import asyncio
import logging
from hashlib import md5

import httpx

from db import get_calendars, get_event, get_calendar
from db import create_event, create_calendar
from db import update_event, update_calendar
from db import delete_calendar
from config import get_calendar_url


logger = logging.getLogger()
logger.setLevel(logging.INFO)
fmt = logging.Formatter('%(asctime)s: [%(levelname)-5s]: %(message)s', '[%y/%m/%d][%H:%M:%S]')
log = logging.StreamHandler()
log.setFormatter(fmt)
file_log = logging.FileHandler('worker.log', encoding='UTF-8')
file_log.setFormatter(fmt)
err_log = logging.FileHandler('worker_crash.log', encoding='UTF-8')
err_log.setLevel(logging.ERROR)
err_log.setFormatter(fmt)
logger.addHandler(log)
logger.addHandler(file_log)
logger.addHandler(err_log)


def error_log(e: Exception, text):
    logger.error(f'[{e}/{type(e)}]: {text}\n')


async def get_calendar_from_site(student_id):
    try:
        response = httpx.get(f'{get_calendar_url}{student_id}', timeout=10)
        raw_events_list = response.json()['data']['raspList']
        logger.info(f'Total - {len(raw_events_list)}')
        if len(raw_events_list) == 0:
            raise ValueError('Site returned no data')
        events_to_create = []
        events_to_update = []
        events_to_delete = []
        old_calendar_dict = await get_calendar(student_id)
        for raw_event in raw_events_list:
            event = cut_event(raw_event)
            event['hash'] = hash_event(event)
            rasp_item_ids = event.pop('rasp_item_ids')
            if len(rasp_item_ids) > 1:
                event_id = sum(rasp_item_ids)
            else:
                event_id = rasp_item_ids[0]
            event_from_db = await get_event(event_id)
            event['rasp_item_id'] = event_id
            if event_from_db is None:
                await create_event(event)
            elif event_from_db.hash != event['hash']:
                await update_event(event)
            if event_id not in old_calendar_dict:
                await create_calendar(student_id, event_id, event['hash'])
                events_to_create.append(event)
            elif old_calendar_dict[event_id] != event['hash']:
                await update_calendar(student_id, event_id, event['hash'])
                events_to_update.append(event)
                old_calendar_dict.pop(event_id)
            else:
                old_calendar_dict.pop(event_id)
        for event_id in old_calendar_dict:
            await delete_calendar(student_id, event_id)
            events_to_delete.append(event_id)
        logger.info(f'To create - {len(events_to_create)}')
        logger.info(f'To update - {len(events_to_update)}')
        logger.info(f'To delete - {len(events_to_delete)}')
        return events_to_create, events_to_update, events_to_delete
    except ValueError as e:
        error_log(e, '[503 Service Temporarily Unavailable - ValueError]')
    except TypeError as e:
        error_log(e, '[503 Service Temporarily Unavailable - TypeError]')
    except httpx.ReadTimeout as e:
        error_log(e, '[ReadTimeout]')
    except httpx.NetworkError as e:
        error_log(e, '[ConnectionError wtf]')
    except Exception as e:
        error_log(e, 'UNKNOWN ERROR')


def cut_event(raw_event):
    info_dict = raw_event['info']
    event = {
        'name': raw_event['name'],
        'color': raw_event['color'],
        'start': raw_event['start'],
        'end': raw_event['end'],
        'rasp_item_ids': raw_event['raspItemsIDs'],
        'aud': info_dict['aud'],
        'link': info_dict['link'],
        'teacher': info_dict['teacher'],
        'module_name': info_dict['moduleName'],
        'theme': info_dict['theme'],
        'group_name': info_dict['groupName'],
        'description': f"Преподаватель: {info_dict.get('teacher', '')}\n"
                       f"Модуль: {info_dict['moduleName']}\n"
                       f"Тема: {info_dict['theme']}\n"
                       f"Группа: {info_dict['groupName']}",
    }
    if event['link']:
        event['description'] = f"{event['link']}\n{event['description']}"
    return event


def hash_event(event):
    return md5(
        str(event['start'] + event['end'] + event['name'] + event['description'] + event['aud']
            ).encode('UTF-8')).hexdigest()


def google_executor(to_google, ts, student_id, calendar_id):
    events_to_create, events_to_update, events_to_delete = to_google
    # print(to_google, ts, student_id, calendar_id)


async def loop():
    while True:
        try:
            calendars = await get_calendars()
            for num, student in enumerate(calendars):
                logger.info(f'({num + 1}/{len(calendars)}) [{student.student_id}] {student.fio}')
                to_google = await get_calendar_from_site(student.student_id)
                logger.info('----------------')
                google_executor(to_google, int(time.time()), student.student_id, student.calendar_id)
                await asyncio.sleep(5)
            await asyncio.sleep(30)
        except Exception as e:
            error_log(e, 'UNKNOWN ERROR IN ROOT')
            await asyncio.sleep(300)


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(loop())
