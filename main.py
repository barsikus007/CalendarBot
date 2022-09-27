import os
import re
import base64
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import suppress


import httpx
from loguru import logger
from aiogram import executor, Bot, Dispatcher
from aiogram.types import Update, Message, BotCommand, ContentTypes, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.utils.exceptions import MessageCantBeDeleted
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from googleapiclient import errors

from src.models import Student
from src.utils import get_logger, get_service
from src.utils.logo import make_image
from src.settings import settings
from src.db.dump_db import dump_db
from src.crud.student import get_student_by_fio, get_student_by_telegram_id, update_student_tg_id, set_student_calendar, \
    get_student_by_student_id, create_student
from worker import parser, get as get_with_tries


logger.remove()
logger = get_logger('bot')


service = get_service()
bot = Bot(token=settings.TELEGRAM_TOKEN)
dp = Dispatcher(bot)
commands_list = [
    BotCommand(command='/start', description='Start the Bot'),
    BotCommand(command='/help', description='Help page about commands'),
    BotCommand(command='/guide', description='Quick video guide for /setup'),
    BotCommand(command='/guide_id', description='Quick video guide for /setup_id'),
    BotCommand(command='/guide_auth', description='Quick video guide for /setup_auth'),
    BotCommand(command='/setup', description='Setup calendar using your name (only for elder courses)'),
    BotCommand(command='/setup_id', description='Setup calendar using id'),
    BotCommand(command='/setup_auth', description='Setup calendar using auth'),
    BotCommand(command='/color', description='Setup colors for calendar'),
    BotCommand(command='/get', description='Generate personal calendar url and link'),
    BotCommand(command='/electives', description='Get electives calendar url and link'),
    BotCommand(command='/logo', description='Generate logo'),
]


class LoggingMiddleware(BaseMiddleware):
    async def on_process_message(self, message: Message, data: dict):
        logger.info(f'[{message.from_user.id}/{message.from_user.mention}]: {message.text}')

    async def on_process_callback_query(self, query: CallbackQuery, data: dict):
        logger.info(f'[{query.from_user.id}/{query.from_user.mention}]: {query.data}')


async def report(text):
    await bot.send_message(chat_id=settings.ADMIN_ID, text=text, disable_notification=True)


async def auth_and_get_id_and_fio(username: str, password: str):
    async with httpx.AsyncClient() as session:
        auth = await session.post(
            settings.AUTH_URL,
            json={'password': password, 'userName': username})
        headers = {'authorization': f"Bearer {auth.json()['data']['accessToken']}"}
        kek = await session.get(settings.AUTH_URL, headers=headers)
        kek.raise_for_status()
        user = kek.json()['data']['user']
        student_id = user['anotherID']
        fio = f"{user['last_name']} {user['first_name']} {user['middle_name']}"
        return student_id, fio


async def create_student_and_check_id(message, student_id, fio):
    if await get_student_by_fio(fio):
        await update_student_tg_id(fio, message.from_user.id)
    elif await get_student_by_student_id(student_id):
        await update_student_tg_id(fio, message.from_user.id)
    else:
        try:
            resp = get_with_tries(f'{settings.GET_CALENDAR_URL}studentID={student_id}', max_tries=10)
            if not resp or resp.state != 1:
                raise ValueError('University api is down or you passed wrong id')
            student = Student(
                id=student_id,
                fio=fio,
                telegram_id=message.from_user.id,
            )
            await create_student(student)
        except Exception as e:
            await message.answer(
                f'Error:\n{e}\n'
                f'Check your link and PM to @{settings.ADMIN_USERNAME} for report problem')
            return
    return True


def create_color(mail, calendar_id):
    logger.info('Creating new color...')
    rule = {
        'scope': {
            'type': 'user',
            'value': mail,
        },
        'role': 'writer'
    }
    service.acl().insert(calendarId=calendar_id, body=rule).execute()
    logger.info('SUCCESS')


async def create_calendar(student_id, tg_id):
    logger.info('Creating new calendar...')
    student = await get_student_by_telegram_id(tg_id)
    _bot = await bot.me
    fio = student.fio.split()
    short_name = f'{fio[0]} {fio[1][0]}. {fio[2][0]}.'
    calendar = {
        'summary': short_name,
        'description': f'Generated and updating by @{_bot.username}',
        'timeZone': 'Europe/Moscow'
    }
    rule = {
        'scope': {'type': 'default'},
        'role': 'reader'
    }
    created_calendar = service.calendars().insert(body=calendar).execute()
    service.acl().insert(calendarId=created_calendar['id'], body=rule).execute()
    await set_student_calendar(student_id, created_calendar['id'])
    logger.info('SUCCESS')
    return created_calendar['id']


async def check_calendar_link(calendar_id, tg_id, student_id):
    try:
        service.calendars().get(calendarId=calendar_id).execute()
        logger.info('Calendar link exist')
    except errors.HttpError as e:
        if e.resp.status != 404:
            raise errors.HttpError('Other error (!=404)') from e
        logger.info(f'No calendar with that link... Strange\n{calendar_id}\n{tg_id}')
        await report('AHTUNG, 404 CAL ERROR')
        calendar_id = await create_calendar(student_id, tg_id)
    logger.info(calendar_id)
    return calendar_id


@dp.errors_handler()
async def errors(event: Update = None, exception: BaseException = None):
    await report(f'{event}\n{type(exception)}\n{exception}')


@dp.message_handler(commands='dump')
async def dump(message: Message):
    if message.from_user.id == settings.ADMIN_ID:
        archive = await dump_db()
        await message.answer_document(document=open(archive, 'rb'))


@dp.message_handler(commands='color')
async def color(message: Message):
    splitted = message.text.split()
    if message.text == '/color example@gmail.com':
        await message.answer('Genius ( ͡° ͜ʖ ͡°)')
        return
    if len(splitted) == 1:
        await message.answer('Example:\n/color example@gmail.com')
    elif len(splitted) > 2:
        await message.answer(f'Wrong input:\n{message.text}\nExample:\n/color example@gmail.com')
    elif not splitted[1].endswith('@gmail.com'):
        await message.answer(f'Only @gmail.com allowed:\n{message.text}\nExample:\n/color example@gmail.com')
    else:
        mail = splitted[1]
        student = await get_student_by_telegram_id(message.from_user.id)
        if student:
            try:
                create_color(mail, student.calendar_id)
                await message.answer('Colors was added to your google calendar')
            except Exception as e:
                await report(f'AHTUNG EXCEPTION:\n{type(e)}\n{e}')
                await message.answer(
                    f'Server error - try again later or contact @{settings.ADMIN_USERNAME} for report problem')
        else:
            await message.answer('Do /setup first')


@dp.message_handler(commands='setup')
async def setup(message: Message):
    splitted = message.text.split()
    if message.text == '/setup Иванов Иван Иванович':
        await message.answer('Genius ( ͡° ͜ʖ ͡°)')
        return
    if len(splitted) == 1:
        await message.answer(
            'Guide for this method: /guide\n'
            'Example:\n'
            '/setup Иванов Иван Иванович')
    elif len(splitted) < 4:
        await message.answer(f'Wrong input:\n{message.text}\nExample:\n/setup Иванов Иван Иванович')
    else:
        fio = ' '.join(splitted[1:])
        student = await get_student_by_fio(fio)
        if student:
            await update_student_tg_id(fio, message.from_user.id)
            await get(message, fio)
        else:
            await message.answer(f'Wrong name:\n{message.text}\nExample:\n/setup Иванов Иван Иванович')


@dp.message_handler(commands='setup_id')
async def setup_id(message: Message):
    splitted = message.text.split()
    if message.text == '/setup_id https://link.to/photo/123456.jpg Иванов Иван Иванович':
        await message.answer('Genius ( ͡° ͜ʖ ͡°)')
        return
    if len(splitted) == 1:
        await message.answer(
            f'Guide for this method: /guide_id\n'
            f'Application link: {settings.WEBAPP_URL}\n'
            f'Example:\n'
            f'/setup_id https://link.to/photo/123456.jpg Иванов Иван Иванович')
    elif len(splitted) < 5:
        await message.answer(
            f'Wrong input:\n'
            f'{message.text}\n'
            f'Example:\n'
            f'/setup_id https://link.to/photo/123456.jpg Иванов Иван Иванович')
    else:
        fio = ' '.join(splitted[2:])
        student_id_link = splitted[1]
        student_id = re.findall(r'.*/(\d{4,10})\.jpg.*', student_id_link)[0]
        success = await create_student_and_check_id(message, student_id, fio)
        if not success:
            return
        await get(message, fio)


@dp.message_handler(commands='setup_auth')
async def setup_auth(message: Message):
    splitted = message.text.split()
    if message.text == '/setup_auth username@gmail.com password':
        await message.answer('Genius ( ͡° ͜ʖ ͡°)')
        return
    if len(splitted) == 1:
        await message.answer(
            'Guide for this method: /guide_auth\n'
            'Example:\n'
            '/setup_auth username@gmail.com password')
    elif len(splitted) != 3:
        await message.answer(f'Wrong input:\n{message.text}\nExample:\n/setup_auth username@gmail.com password')
    else:
        username, password = splitted[1:]
        try:
            student_id, fio = await auth_and_get_id_and_fio(username, password)
        except Exception as e:
            await message.answer(
                f'Error:\n{e}\n'
                f'Check your username and password and PM to @{settings.ADMIN_USERNAME} for report problem')
            return
        success = await create_student_and_check_id(message, student_id, fio)
        if not success:
            return
        await get(message, fio)


@dp.message_handler(commands='get')
async def get(message: Message, fio=None):
    if fio:
        user_data = await get_student_by_fio(fio)
    else:
        user_data = await get_student_by_telegram_id(message.from_user.id)
    if not user_data:
        await message.answer('Please type /setup first!')
        return
    await message.answer('Generating your link...')
    calendar_id = user_data.calendar_id
    if calendar_id is None:
        calendar_id = await create_calendar(user_data.id, message.from_user.id)
        if not calendar_id:
            await message.answer(
                f'Server error - try again later or contact @{settings.ADMIN_USERNAME} for report problem')
            return
    calendar_id = await check_calendar_link(calendar_id, message.from_user.id, user_data.id)
    base64_link = base64.b64encode(calendar_id.encode('ascii')).decode('ascii').replace('=', '')
    calendar_url = f'https://calendar.google.com/calendar/u/0?cid={base64_link}'
    await message.answer(
        text=f'Ok here is your Google Calendar id:\n'
             f'{calendar_id}\n'
             f'It will be filled within 15 minutes\n'
             f'\n'
             f'If you are PC user use calendar link instead:\n'
             f'{calendar_url}\n'
             f'If your are APPLE user import ics file instead:\n'
             f'https://calendar.google.com/calendar/ical/{calendar_id.split("@")[0]}%40group.calendar.google.com/public/basic.ics',
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton('How to add?', callback_data='how_to')))


@dp.message_handler(commands='electives')
async def electives(message: Message):
    calendar_id = settings.ELECTIVES_CALENDAR_ID
    base64_link = base64.b64encode(calendar_id.encode('ascii')).decode('ascii').replace('=', '')
    calendar_url = f'https://calendar.google.com/calendar/u/0?cid={base64_link}'
    await message.answer(
        f'Ok here is electives Google Calendar id:\n'
        f'{calendar_id}\n'
        f'\n'
        f'If you are PC user use calendar link instead:\n'
        f'{calendar_url}\n'
        f'If your are APPLE user import ics file instead:\n'
        f'https://calendar.google.com/calendar/ical/{calendar_id.split("@")[0]}%40group.calendar.google.com/public/basic.ics',
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton('How to add?', callback_data='how_to')))


@dp.message_handler(commands='logs')
async def log_analyze(message: Message):
    if message.from_user.id != settings.ADMIN_ID:
        return
    log_folder = Path('logs')
    yesterday_bot_log = log_folder / 'bot' / ((datetime.now() - timedelta(1)).strftime('%y-%m-%d') + '-crash.log')
    yesterday_worker_log = log_folder / 'worker' / ((datetime.now() - timedelta(1)).strftime('%y-%m-%d') + '-crash.log')
    today_bot_log = log_folder / 'bot' / (datetime.now().strftime('%y-%m-%d') + '-crash.log')
    today_worker_log = log_folder / 'worker' / (datetime.now().strftime('%y-%m-%d') + '-crash.log')
    count_yesterday_bot_log = None
    count_yesterday_worker_log = None
    count_today_bot_log = None
    count_today_worker_log = None
    if yesterday_bot_log.exists():
        with open(yesterday_bot_log) as f:
            count_yesterday_bot_log = len([_ for _ in f.readlines() if _.find('| ERROR   |') != -1])
    if yesterday_worker_log.exists():
        with open(yesterday_worker_log) as f:
            count_yesterday_worker_log = len([_ for _ in f.readlines() if _.find('| ERROR   |') != -1])
    if today_bot_log.exists():
        with open(today_bot_log) as f:
            count_today_bot_log = len([_ for _ in f.readlines() if _.find('| ERROR   |') != -1])
    if today_worker_log.exists():
        with open(today_worker_log) as f:
            count_today_worker_log = len([_ for _ in f.readlines() if _.find('| ERROR   |') != -1])
    await message.answer(
        f'Logs\n'
        f'{count_yesterday_bot_log=}\n'
        f'{count_yesterday_worker_log=}\n'
        f'{count_today_bot_log=}\n'
        f'{count_today_worker_log=}'
    )


@dp.message_handler(commands='logo')
async def logo_gen(message: Message):
    args = message.text.split()[1:]
    if len(args) != 8:
        return await message.answer(
            f'`/logo n  r   g   b   side x    y    background`\n'
            f'`/logo 20 255 255 255 100  1920 1080 16777215`\n'
            f'n = number of polygons\n'
            f'r, g, b = accent color (polygons will fade from this to black)\n'
            f'side = polygon\'s side size\n'
            f'x, y = resolution of result image\n'
            f'background = background color (r\*g\*b) (use 256\*256\*256=16777215 for white, 0\*0\*0=0 for black)\n',
            parse_mode='Markdown'
        )
    try:
        args = [*map(int, args)]
    except Exception as e:
        return await message.answer(f'Incorrect format {e}')
    n, r, g, b, side, x, y, background = args
    if not (
            (50 >= n >= 3) and
            (256 > r >= 0) and (256 > g >= 0) and (256 > b >= 0) and (1000 >= side > 0) and
            (3840 >= x >= 640) and (2160 >= y >= 480) and (16777216 > background >= 0)
    ):
        return await message.answer(
            'Args is invalid:\n'
            f'(50 >= {n=} >= 3) (256 > {r=} >= 0) (256 > {g=} >= 0) (256 > {b=} >= 0) (1000 >= {side=} > 0) and\n'
            f'(3840 >= {x=} >= 640) and (2160 >= {y=} >= 480) and (16777216 > {background=} >= 0)'
        )
    filename = f'{hash(message)}.png'
    try:
        make_image(
            n=n,
            color=(r, g, b),
            show_image=False,
            save_image=filename,
            side=side,
            resolution=(x, y),
            background=background
        )
    except Exception as e:
        return await message.answer(f'Incorrect format {e}')
    await message.answer_document(open(filename, 'rb'))
    os.remove(filename)


@dp.message_handler(commands='help')
async def help_cmd(message: Message):
    await message.answer(
        '/setup\n'
        '/get'
    )


@dp.message_handler(commands='guide')
async def guide(message: Message):
    await message.answer_video(
        caption='Take it!',
        video=settings.GIF_GUIDE,
    )


@dp.message_handler(commands='guide_id')
async def guide_id(message: Message):
    await message.answer_video(
        caption='Take it!',
        video=settings.GIF_GUIDE_ID,
    )


@dp.message_handler(commands='guide_auth')
async def guide_auth(message: Message):
    await message.answer_video(
        caption='Take it!',
        video=settings.GIF_GUIDE_AUTH,
    )


@dp.message_handler(commands='start')
async def start_cmd(message: Message):
    if message.from_user.id == settings.ADMIN_ID:
        await bot.set_my_commands(commands_list)
    await message.answer(
        'For the first time you need to setup name via /setup\n'
        'If you have troubles with /setup, you could try /setup_id and /setup_auth\n'
        'After than you can get calendar link via /get\n'
        'To add colors use /color\n'
        'To remove previous calendar use /remove\n'
        'To show full guide type /guide'
    )


@dp.callback_query_handler(text='google')
async def google(query: CallbackQuery):
    message = query.message
    await message.answer_video(
        caption='How to import calendar to normal devices:\n'
                'https://calendar.google.com/calendar/r/settings/addcalendar',
        video=settings.GIF_GOOGLE,
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton('How to add?', callback_data='how_to')))
    with suppress(MessageCantBeDeleted):
        await message.delete()
    await query.answer('Rolling back...')


@dp.callback_query_handler(text='apple')
async def apple(query: CallbackQuery):
    message = query.message
    await message.answer(
        text='Choose your IOS version: (PM me if you have IOS 13 and its different)',
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton('IOS 12', callback_data='ios12'),
            InlineKeyboardButton('IOS 14', callback_data='ios14')))
    with suppress(MessageCantBeDeleted):
        await message.delete()
    await query.answer('Rolling back...')


@dp.callback_query_handler(text='ios12')
async def ios12(query: CallbackQuery):
    message = query.message
    await message.answer_video(
        caption='How to import calendar to apple IOS 12 devices:',
        video=settings.GIF_IOS12,
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton('How to add?', callback_data='how_to')))
    with suppress(MessageCantBeDeleted):
        await message.delete()
    await query.answer('Rolling back...')


@dp.callback_query_handler(text='ios14')
async def ios14(query: CallbackQuery):
    message = query.message
    await message.answer_video(
        caption='How to import calendar to apple IOS 14 devices:',
        video=settings.GIF_IOS14,
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton('How to add?', callback_data='how_to')))
    with suppress(MessageCantBeDeleted):
        await message.delete()
    await query.answer('Rolling back...')


@dp.callback_query_handler(text='how_to')
async def how_to_er(query: CallbackQuery):
    message = query.message
    await message.answer(
        text='Choose your platform:',
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton('Apple', callback_data='apple'),
            InlineKeyboardButton('Other', callback_data='google')))
    await query.answer('Check that!')


@dp.message_handler(content_types=ContentTypes.ANY)
async def all_other_messages(message: Message):
    await message.answer('Type /start')


if __name__ == '__main__':
    scheduler = AsyncIOScheduler()
    scheduler.add_job(parser, 'date', run_date=datetime.now())
    dp.middleware.setup(LoggingMiddleware())
    scheduler.start()
    executor.start_polling(dp)
    scheduler.shutdown()
