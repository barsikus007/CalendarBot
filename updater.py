import pickle
import logging
from time import sleep
from hashlib import md5
from datetime import datetime, timezone

import httpx
import ujson as json
from googleapiclient import errors
from googleapiclient.discovery import build


logger = logging.getLogger()
logger.setLevel(logging.INFO)
fmt = logging.Formatter('%(asctime)s: [%(levelname)-5s]: %(message)s', '[%y/%m/%d][%H:%M:%S]')
log = logging.StreamHandler()
log.setFormatter(fmt)
errlog = logging.FileHandler('crash.log', encoding='UTF-8')
errlog.setLevel(logging.ERROR)
errlog.setFormatter(fmt)
logger.addHandler(log)
logger.addHandler(errlog)


def error_log(e, text):
    logger.error(f'[{e}/{type(e)}]: {text}\n')


def get_name(user_id):
    with open('Students.json', 'rb') as f:
        students_list = json.load(f)['data']['allStudent']
        for student in students_list:
            if student['studentID'] == user_id:
                return student['fio']


def dump_calendar(user_id, calendar_link):
    with open('calendars.pickle', 'rb') as f:
        calendars = pickle.load(f)
    calendars[user_id] = calendar_link
    with open('calendars.pickle', 'wb') as f:
        pickle.dump(calendars, f)


def converter(calendar_json):
    ics_json = []
    for event in calendar_json:
        event_dict = dict()
        start = datetime.strptime(event['start'], '%Y-%m-%dT%H:%M:%S+03:00').astimezone(timezone.utc)
        end = datetime.strptime(event['end'], '%Y-%m-%dT%H:%M:%S+03:00').astimezone(timezone.utc)
        event_dict['Subject'] = event['name']
        event_dict['Start'] = start.isoformat()[:-6] + 'Z'
        event_dict['End'] = end.isoformat()[:-6] + 'Z'
        description_raw = event['info']
        description = f"""Преподаватель: {description_raw['teacher']}
Модуль: {description_raw['moduleName']}
Тема: {description_raw['theme']}
Группа: {description_raw['groupName']}"""
        event_dict['Description'] = description
        event_dict['Location'] = description_raw['aud']
        event_dict['groupName'] = description_raw['groupName']
        event_dict['hash'] = description_raw['raspItemID']
        event_dict['link'] = f'{description_raw["link"]}\n' if description_raw['link'] else ''
        ics_json.append(event_dict)
    return ics_json


def generator(events_json):
    events = []
    for event in events_json:
        hash_plus = str(event['hash']) + '0000'
        events.append(
            {
                'summary': event["Subject"],
                'location': event['Location'],
                'description': f'{event["link"]}{event["Description"]}',
                'id': hash_plus,
                'start': {
                    'dateTime': event["Start"],
                    'timeZone': 'Europe/Moscow',
                },
                'end': {
                    'dateTime': event["End"],
                    'timeZone': 'Europe/Moscow',
                },
            })
    print('U')
    # from pprint import pp
    # pp(events)
    # exit()
    return events


def get_events(student_id, debug=False):
    try:
        response = httpx.get(f'https://edu.donstu.ru/api/RaspManager?studentID={student_id}', timeout=10)
        if debug:
            return response
        print(f"{datetime.now().strftime('[%d.%m.%y][%H:%M:%S]')}: [INFO ]: P", end='')
        calendar_json = response.json()['data']['raspList']
    except ValueError as e:
        error_log(e, '[503 Service Temporarily Unavailable - ValueError]')
        calendar_json = dict()
    except TypeError as e:
        error_log(e, '[503 Service Temporarily Unavailable - TypeError]')
        calendar_json = dict()
    except httpx.ReadTimeout as e:
        error_log(e, '[ReadTimeout]')
        calendar_json = dict()
    except httpx.NetworkError as e:
        error_log(e, '[ConnectionError wtf]')
        calendar_json = dict()
    except Exception as e:
        error_log(e, 'UNKNOWN ERROR')
        calendar_json = dict()

    print('C', end='')
    event_json = converter(calendar_json)

    print('G', end='')
    return generator(event_json)


class Updater:
    def __init__(self):
        self.service = self.token_init()
        if self.service is None:
            return

    def token_init(self):
        try:
            logger.info(f'Program started...')
            with open('token.pickle', 'rb') as token:
                credentials = pickle.load(token)
            service = build('calendar', 'v3', credentials=credentials)
            logger.info(f'Token - OK')
            return service
        except Exception as e:
            error_log(e, 'TOKEN INIT ERROR')
            return None

    def start(self):
        while True:
            try:
                self.loop()
            except Exception as e:
                error_log(e, 'VERY UNKNOWN ERROR')

    def loop(self):
        with open('calendars.pickle', 'rb') as f:
            self.users = pickle.load(f)
        total_users = len(self.users)
        logger.info(f'Users in database - {total_users}')
        for number, (user_id, calendar_link) in enumerate(self.users.items()):
            number += 1
            fio = get_name(user_id)
            logger.info(f'User {number}/{len(self.users)} - {fio}')
            # Skipper
            # if number != 29:
            #     continue
            calendar_link = self.get_calendars(fio, user_id, calendar_link)
            # google_events = self.get_events(user_id, calendar_link)
            # TODO ids = [i['id'] for i in google_events]
            events = get_events(user_id)
            logger.info(f'Total events - {len(events)}')
            if len(events) == 0:
                logger.info(f'Skip')
                sleep(5)
                continue
            with open('hashes.pickle', 'rb') as f:
                db = pickle.load(f)
            ###
            # if number == 29:
            #     # dump = db.get(user_id)
            #     # with open('dump.pickle', 'wb') as f:
            #     #     pickle.dump(events, f)
            #     with open('dump.pickle', 'rb') as f:
            #         dump = pickle.load(f)

            #     old_db = self.hash_events(dump)
            #     new_db = self.hash_events(events)
            #     print(1)
            #     exit()
            ###
            if db.get(user_id):
                old_db = db[user_id]
                new_db = self.hash_events(events)
                db[user_id] = new_db
                events = self.cut_events(events, old_db, new_db)
            else:
                new_db = self.hash_events(events)
                db[user_id] = new_db
            if len(events) == 0:
                logger.info(f'Skip')
                sleep(5)
                continue
            sleep(1)
            self.set_events(events, fio, calendar_link)
            with open('hashes.pickle', 'wb') as f:
                pickle.dump(db, f)
            sleep(5)
        logger.info('End of users dict waiting for 10 secs')
        sleep(10)

    def get_calendars(self, fio, user_id, calendar_link):
        try:
            calendar_link = self.service.calendars().get(calendarId=calendar_link).execute()['id']
            self.service.calendarList().get(calendarId=calendar_link).execute()
            return calendar_link
        except errors.HttpError as e:
            if e.resp.status == 404:
                error_log(e, f'Calendar not found\n{user_id}\n{calendar_link}')
                calendar = {
                    'summary': fio,
                    'description': 'Generated and updating by @donstux_bot',
                    'timeZone': 'Europe/Moscow'
                }
                rule = {
                    'scope': {'type': 'default'},
                    'role': 'reader'
                }
                calendar_link = self.service.calendars().insert(body=calendar).execute()['id']
                self.service.acl().insert(calendarId=calendar_link, body=rule).execute()
                dump_calendar(user_id, calendar_link)
                logger.info('SUCCESS CALENDAR CREATION')
            else:
                error_log(e, f'Unknown calendar error\n{user_id}\n{calendar_link}')

    def get_events(self, user_id, calendar_link):
        try:
            google_events = self.service.events().list(calendarId=calendar_link, maxResults=2500).execute()['items']
            google_events.sort(key=lambda x: int(x['id']))
            return google_events
        except errors.HttpError as e:
            error_log(e, f'Unknown calendar events error\n{user_id}\n{calendar_link}')

    def cut_events(self, events, old_db, new_db):
        if old_db[0] == new_db[0]:
            return {}
        # TODO если равны то найти что обновить и обновить
        # TODO если равны то евенты в хуй пойми каком порядке могут быть впринципе алгоритм ниже работает но надо
        # TODO подумать по идее можно сортировать массив с хешами перед подсчетом финального
        # elif old_db[1].keys() == new_db[1].keys():
        #     new_events = []
        #     # for old, new in zip(old_db[1].values(), new_db[1].values()):
        #     for (i, old), (j, new) in zip(old_db[1].items(), new_db[1].items()):
        #         if old != new:
        #             for event in events:
        #                 ids = int(event['id'])//10000
        #                 if ids == j:
        #                     new_events.append(event)
        #     return new_events
        # TODO если не равны то найти что убралось и убрать transparency status
        # TODO https://developers.google.com/calendar/v3/reference/events#resource
        # TODO если нечего убрать то найти что добавить и заменить (пропатчить)
        else:
            return events
            # new_events = []
            # # for old, new in zip(old_db[1].values(), new_db[1].values()):
            # for (i, old), (j, new) in zip(old_db[1].items(), new_db[1].items()):
            #     if i != j:
            #         for event in events:
            #             ids = int(event['id'])//10000
            #             if ids == j:
            #                 new_events.append(event)
            #     if old != new:
            #         for event in events:
            #             ids = int(event['id'])//10000
            #             if ids == j:
            #                 new_events.append(event)
            # return new_events

    def set_events(self, events, fio, calendar_link):
        for counter, event in enumerate(events):
            counter += 1
            logger.info(f'Patching event {counter}/{len(events)} for {fio}')
            # Skipper
            # if counter < 60:
            #     continue
            # if counter == 76 and fio == 'Рест В. С.':
            #     print('Skipped')
            #     continue
            # if counter == 75 and fio == 'Решетников В. П.':
            #     print('Skipped')
            #     continue
            sleep(0.5)
            try:
                self.service.events().patch(calendarId=calendar_link, body=event, eventId=event['id']).execute()
            except errors.HttpError as e:
                if e.resp.status == 403:
                    logger.info('403 ERROR Sleeping for 10 secs')
                    sleep(10)
                    self.service.events().patch(calendarId=calendar_link, body=event, eventId=event['id']).execute()
                    error_log(e, f'403 ERROR')
                elif e.resp.status == 404:
                    logger.info('Creating event...')
                    self.service.events().insert(calendarId=calendar_link, body=event).execute()
                elif e.resp.status == 503:
                    logger.info('503 ERROR WTF?!')
                    error_log(e, f'Backend Error?')
                else:
                    error_log(e, f'UNKNOWN HTTP ERROR')
            except ConnectionResetError as e:
                error_log(e, f'[WinError ConnectionResetError]')
            except OSError as e:
                error_log(e, f'OSError')
            except Exception as e:
                error_log(e, f'UNKNOWN ERROR')

    def remove_event(self, event):
        pass

    def hash_events(self, events):
        ids = []
        hashsums = []
        for event in events:
            sorted_event = dict()
            sorted_event['start'] = dict(sorted(event['start'].items(), key=lambda x: x[0]))
            sorted_event['end'] = dict(sorted(event['end'].items(), key=lambda x: x[0]))
            sorted_event = dict(sorted(event.items(), key=lambda x: x[0]))
            text_event = ''
            start = sorted_event['start']
            sorted_event['start'] = ''
            ids.append(int(event['id']) // 10000)
            for el in start.items():
                sorted_event['start'] += el[1]
            end = sorted_event['end']
            sorted_event['end'] = ''
            for el in end.items():
                sorted_event['end'] += el[1]
            for el in sorted_event.items():
                text_event += el[1]
            coded = text_event.encode('UTF-8')
            hashsums.append(md5(coded).hexdigest())
        hashsum_string = ''.join(hashsums)
        new_db = (md5(hashsum_string.encode('UTF-8')).hexdigest(), {k: v for k, v in zip(ids, hashsums)})
        # print(new_db)
        return new_db


if __name__ == '__main__':
    upd = Updater()
    upd.start()
    # & '.\Desktop\Launchers\gcal updater.bat'
    # oauth2client
