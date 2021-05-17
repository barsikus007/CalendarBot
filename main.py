import pickle
import base64
from datetime import datetime

import ujson as json
import aiohttp
from aiogram import md, executor, Bot, Dispatcher
from aiogram.types import Update, Message, BotCommand, ContentTypes, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.middlewares import BaseMiddleware
from googleapiclient import errors

from db import get_student_by_fio, update_student_tg_id, get_student_by_telegram_id, set_student_calendar
from utils import get_logger, get_service, async_session
from config import TOKEN, admin_id

'''
Unofficial donstux bot by @ogu_rez
To start type /start
'''

logger = get_logger('main')
service = get_service(logger)
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
commands = [
    BotCommand(command='/start', description='Start the Bot'),
    BotCommand(command='/help', description='Help page about commands'),
    BotCommand(command='/guide', description='Quick video how to use bot'),
    BotCommand(command='/change_lang', description='Change language'),
    BotCommand(command='/setup', description='Choose groups for calendar'),
    BotCommand(command='/get', description='Generate personal calendar url and link'),
    BotCommand(command='/get_aud', description='Get events by aud'),
]


class LoggingMiddleware(BaseMiddleware):
    async def on_process_message(self, message: Message, data: dict):
        logger.info(f'[{message.from_user.id}/{message.from_user.mention}]: {message.text}')

    async def on_process_callback_query(self, query: CallbackQuery, data: dict):
        logger.info(f'[{query.from_user.id}/{query.from_user.mention}]: {query.data}')


async def report(text):
    await bot.send_message(chat_id=admin_id, text=text, disable_notification=True)


def get_aud_id(aud_name):
    with open('auds.pickle', 'rb') as f:
        auds = pickle.load(f)['data']
    for aud in auds:
        if aud['name'] == aud_name:
            return aud['id']


def get_name(user_id):
    with open('Students.json', 'rb') as f:
        students_list = json.load(f)['data']['allStudent']
        for student in students_list:
            if student['studentID'] == user_id:
                return student['fio']


async def create_calendar(user_id):
    logger.info('Creating new calendar...')
    calendar = {
        'summary': get_name(user_id),
        'description': 'Generated and updating by @donstux_bot',
        'timeZone': 'Europe/Moscow'
    }
    rule = {
        'scope': {'type': 'default'},
        'role': 'reader'
    }
    created_calendar = service.calendars().insert(body=calendar).execute()
    service.acl().insert(calendarId=created_calendar['id'], body=rule).execute()
    await set_student_calendar(user_id, created_calendar['id'])
    logger.info('SUCCESS')
    return created_calendar['id']


async def check_calendar_link(calendar_id, user_id):
    try:
        service.calendars().get(calendarId=calendar_id).execute()
        logger.info('Calendar link exist')
    except errors.HttpError as e:
        if e.resp.status == 404:
            logger.info(f'No calendar with that link... Strange\n{calendar_id}\n{user_id}')
            await bot.send_message(chat_id=admin_id, text='AHTUNG, 404 ERROR')
            calendar_id = await create_calendar(user_id)
        else:
            raise errors.HttpError('Other error (!=404)')
    logger.info(calendar_id)
    return calendar_id


@dp.errors_handler()
async def errors(event: Update = None, exception: BaseException = None):
    await report(f'{event}\n{type(exception)}\n{exception}')


@dp.message_handler(commands='dump')
async def dump(message: Message):
    if message.from_user.id == admin_id:
        await message.answer_document(document=open('csv/calendar.csv', 'rb'))
        await message.answer_document(document=open('csv/events.csv', 'rb'))
        await message.answer_document(document=open('csv/students.csv', 'rb'))


@dp.message_handler(commands='setup')
async def setup(message: Message):
    splitted = message.text.split()
    if message.text == '/setup Иванов Иван Иванович':
        await message.answer('Genius ( ͡° ͜ʖ ͡°)')
        return
    if len(splitted) == 1:
        await message.answer(f'Example:\n/setup Иванов Иван Иванович')
    elif len(splitted) < 4:
        await message.answer(f'Wrong input:\n{message.text}\nExample:\n/setup Иванов Иван Иванович')
    else:
        fio = ' '.join(splitted[1:])
        student = await get_student_by_fio(fio)
        if student:
            await update_student_tg_id(fio, message.from_user.id)
            await get(message)
        else:
            await message.answer(f'Wrong name:\n{message.text}\nExample:\n/setup Иванов Иван Иванович')


@dp.message_handler(commands='get')
async def get(message: Message):
    user_data = await get_student_by_telegram_id(message.from_user.id)
    if not user_data:
        await message.answer('Please type /setup first!')
        return
    await message.answer('Generating your link...')
    calendar_id = user_data.calendar_id
    if calendar_id is None:
        calendar_id = await create_calendar(user_data.student_id)
        if not calendar_id:
            await message.answer('Server error - try again later or contact @ogu_rez for report problem')
            return
    calendar_id = await check_calendar_link(calendar_id, message.from_user.id)
    base64_link = base64.b64encode(calendar_id.encode('ascii')).decode('ascii').replace('=', '')
    calendar_url = f'https://calendar.google.com/calendar/u/0?cid={base64_link}'
    await message.answer(
        text=f'Ok here is your Google Calendar id:\n'
             f'{calendar_id}\n'
             f'It will be filled within 15 minutes\n'
             f'\n'
             f'If you are PC user use calendar link instead:\n'
             f'{calendar_url}\n'
             f'If you are APPLE user import ics file instead:\n'
             f'https://calendar.google.com/calendar/ical/{calendar_id.split("@")[0]}%40group.calendar.google.com/public/basic.ics',
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton('How to add?', callback_data='how_to')))


@dp.message_handler(commands='get_aud')
async def get_aud(message: Message):
    if message.text == '/get_aud 8-612':
        await message.answer('Genius ( ͡° ͜ʖ ͡°)')
        return
    date = datetime.now().strftime('%Y-%m-%d')
    aud_id = get_aud_id(message.text.split()[-1])
    if aud_id:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
                async with session.get(f'https://edu.donstu.ru/api/Rasp?idAudLine={aud_id}&sdate={date}') as response:
                    events = await response.json()
            text = f"Classes in {message.text.split()[-1]} at {datetime.now().strftime('%d.%m.%Y')}:\n\n"
            if events['data'] is None:
                await message.answer(
                    f"No classes in {message.text.split()[-1]} at {datetime.now().strftime('%d.%m.%Y')}")
                return
            for event in events['data']['rasp']:
                event_date = event['дата'][:10]
                if event_date == date:
                    time_str = event['часы'].replace('-', ':').replace('\n', ' ').split()
                    text += f"FROM {time_str[0]} TO {time_str[1]}\n" \
                            f"Class {event['дисциплина']}\n" \
                            f"Teacher {event['преподаватель']}\n" \
                            f"Group {event['группа']}\n\n"
        except Exception as e:
            await bot.send_message(chat_id=admin_id, text=f'AHTUNG EXCEPTION:\n{type(e)}\n{e}')
            logger.info(type(e))
            logger.info(e)
            await message.answer('Server error')
            return
        await message.answer(text)
    else:
        await message.answer(f'Wrong auditory\n{message.text}\nExample:\n/get_aud 8-612')


@dp.message_handler(commands='help')
async def help_cmd(message: Message):
    await message.answer(
        f'/setup\n'
        f'/get'
    )


@dp.message_handler(commands='guide')
async def guide(message: Message):
    await message.answer_video(
        caption='Take it!',
        video='BAACAgIAAxkBAAILJ19zIf-u66UuT4iPXZgMYpsNaNp3AAKQCAACmKGhS4GiuulwDSSfGwQ'
    )


@dp.message_handler(commands='start')
async def start_cmd(message: Message):
    await bot.set_my_commands(commands)
    await message.answer('For the first time you need to setup name via /setup\n'
                         'After than you can get calendar link via /get\n'
                         'To remove previous calendar use /remove\n'
                         'To show full guide type /guide')


@dp.callback_query_handler(text='google')
async def google(query: CallbackQuery):
    message = query.message
    await message.answer_video(
        caption='Here is guide how to import calendar to normal devices:\n'
                'https://calendar.google.com/calendar/r/settings/addcalendar',
        video='BAACAgIAAxkBAAILI19zITUx2Y63QZaESS2J6ZzPvXAFAAKOCAACmKGhS0H3HEyivX0-GwQ')
    await query.answer(f'Here you go!')


@dp.callback_query_handler(text='apple')
async def apple(query: CallbackQuery):
    message = query.message
    await message.answer(
        text='Choose your IOS version: (PM me if you have IOS 13)',
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton('IOS 12', callback_data='ios12'),
            InlineKeyboardButton('IOS 14', callback_data='ios14')))
    await message.delete()
    await query.answer(f'Here you go!')


@dp.callback_query_handler(text='ios12')
async def ios12(query: CallbackQuery):
    message = query.message
    await message.answer_video(
        caption='Here is guide how to import calendar to apple IOS 12 devices:',
        video='BAACAgIAAxkBAAIPQl_MG0MKEhfFftbuoriC5mbbWBv9AAK2CgACp_VhSvfYLTSvrUeuHgQ',
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton('How to add?', callback_data='how_to')))
    await message.delete()
    await query.answer(f'Here you go!')


@dp.callback_query_handler(text='ios14')
async def ios14(query: CallbackQuery):
    message = query.message
    await message.answer_video(
        caption='Here is guide how to import calendar to apple IOS 14 devices:',
        video='BAACAgIAAxkBAAIPIV_MDyqvQ5l4aVuFNvW9v-kEYLC_AAKjCgACrhnpSZbHuSG9ZSOLHgQ',
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton('How to add?', callback_data='how_to')))
    await message.delete()
    await query.answer(f'Here you go!')


@dp.callback_query_handler(text='how_to')
async def how_to_er(query: CallbackQuery):
    message = query.message
    await message.answer(
        text='Choose your platform:',
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton('Apple', callback_data='apple'),
            InlineKeyboardButton('Other', callback_data='google')))
    await query.answer(f'Here you go!')


@dp.message_handler(content_types=ContentTypes.ANY)
async def all_other_messages(message: Message):
    await message.answer('Type /start')


if __name__ == '__main__':
    dp.middleware.setup(LoggingMiddleware())
    executor.start_polling(dp)
