import os
import asyncio
from hashlib import md5
from datetime import datetime

import httpx
from googleapiclient import errors
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from db import get_calendars, get_event, get_calendar
from db import create_event, create_calendar
from db import update_event, update_calendar
from db import delete_calendar
from config import get_calendar_url, logger


def error_log(e: Exception, text):
    logger.error(f'[{e}/{type(e)}]: {text}')


def get_calendar_from_site(student_id):
    response = httpx.get(f'{get_calendar_url}{student_id}', timeout=10)
    raw_events_list = response.json()['data']['raspList']
    logger.info(f'Total - {len(raw_events_list)}')
    if len(raw_events_list) == 0:
        raise ValueError('Site returned no data')
    return raw_events_list


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
        'teacher': '' if info_dict['teacher'] is None else info_dict['teacher'],
        'module_name': info_dict['moduleName'],
        'theme': info_dict['theme'],
        'group_name': info_dict['groupName'],
        'description': f"Преподаватель: {'' if info_dict['teacher'] is None else info_dict['teacher']}\n"
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


async def calendar_executor(student_id):
    try:
        events_to_create = []
        events_to_update = []
        old_calendar_dict = await get_calendar(student_id)
        for raw_event in get_calendar_from_site(student_id):
            event = cut_event(raw_event)
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
        error_log(e, '[UNKNOWN ERROR IN CALENDAR EXECUTOR]')


def get_service():
    scopes = ['https://www.googleapis.com/auth/calendar']
    """
    Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    credentials = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        credentials = Credentials.from_authorized_user_file('token.json', scopes)
    # If there are no (valid) credentials available, let the user log in.
    if not credentials or not credentials.valid:
        logger.warning('Token - Invalid')
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', scopes)
            credentials = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(credentials.to_json())
        logger.info('Token - Refreshed')
    logger.info('Token - OK')
    return build('calendar', 'v3', credentials=credentials, cache_discovery=False)


async def google_executor(service, to_google, student_id, calendar_id):
    events_to_create, events_to_update, events_to_delete = to_google
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
        await asyncio.sleep(0.5)
        body = {
            'status': 'confirmed',
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
                await asyncio.sleep(10)
            elif not create and e.resp.status == 404:
                logger.info('404 ERROR, CREATING...')
                return service.events().insert(calendarId=calendar_id, body=body).execute()
            elif create and e.resp.status == 409:
                logger.info('409 ERROR, PATCHING...')
                return service.events().patch(calendarId=calendar_id, eventId=body['id'], body=body).execute()
            elif e.resp.status == 503:
                logger.info('503 ERROR SLEEPING...')
                error_log(e, '[Backend Error]')
                await asyncio.sleep(10)
            else:
                error_log(e, f'[UNKNOWN HTTP ERROR IN EVENT CREATE]')
        except Exception as e:
            error_log(e, '[UNKNOWN ERROR IN EVENT CREATE]')
            await asyncio.sleep(10)


async def delete_google_event(service, calendar_id, event_id):
    while True:
        await asyncio.sleep(0.5)
        try:
            request = service.events().patch(calendarId=calendar_id, eventId=event_id, body={'status': 'cancelled'})
            return request.execute()
        except errors.HttpError as e:
            if e.resp.status == 403:
                logger.info('403 ERROR SLEEPING...')
                await asyncio.sleep(10)
            elif e.resp.status == 503:
                logger.info('503 ERROR SLEEPING...')
                error_log(e, '[Backend Error?]')
                await asyncio.sleep(10)
            else:
                error_log(e, f'[UNKNOWN HTTP ERROR IN EVENT DELETE]')
        # except ConnectionResetError as e:
        #     error_log(e, '[WinError ConnectionResetError]')
        # except OSError as e:
        #     error_log(e, '[OSError]')
        except Exception as e:
            error_log(e, '[UNKNOWN ERROR IN EVENT DELETE]')
            await asyncio.sleep(10)


async def loop():
    while True:
        try:
            service = get_service()
            calendars = await get_calendars()
            for num, student in enumerate(calendars):
                # TODO
                if student.student_id != 256720:
                    continue
                # TODO
                logger.info(f'({num + 1}/{len(calendars)}) #{student.student_id} - {student.fio}')
                to_google = await calendar_executor(student.student_id)
                await google_executor(service, to_google, student.student_id, student.calendar_id)
                await asyncio.sleep(5)
            logger.info('Last user, sleeping...')
            await asyncio.sleep(10)
        except Exception as e:
            error_log(e, '[UNKNOWN ERROR IN LOOP]')
            await asyncio.sleep(300)


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(loop())
