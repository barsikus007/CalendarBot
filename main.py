import base64
from datetime import datetime

from aiogram import executor, Bot, Dispatcher
from aiogram.types import Update, Message, BotCommand, ContentTypes, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.utils.exceptions import MessageCantBeDeleted
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from googleapiclient import errors

from utils import get_logger, get_service
from src.settings import settings
from src.db.dump_db import dump_db
from src.crud.student import get_student_by_fio, get_student_by_telegram_id, update_student_tg_id, set_student_calendar
from worker import parser


logger = get_logger('bot')


service = get_service(logger)
bot = Bot(token=settings.TELEGRAM_TOKEN)
dp = Dispatcher(bot)
commands_list = [
    BotCommand(command='/start', description='Start the Bot'),
    BotCommand(command='/help', description='Help page about commands'),
    BotCommand(command='/guide', description='Quick video guide'),
    BotCommand(command='/setup', description='Choose your name for calendar'),
    BotCommand(command='/color', description='Setup colors for calendar'),
    BotCommand(command='/get', description='Generate personal calendar url and link'),
]


class LoggingMiddleware(BaseMiddleware):
    async def on_process_message(self, message: Message, data: dict):
        logger.info(f'[{message.from_user.id}/{message.from_user.mention}]: {message.text}')

    async def on_process_callback_query(self, query: CallbackQuery, data: dict):
        logger.info(f'[{query.from_user.id}/{query.from_user.mention}]: {query.data}')


async def report(text):
    await bot.send_message(chat_id=settings.ADMIN_ID, text=text, disable_notification=True)


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
    calendar = {
        'summary': student.dict()['short_name'],
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
        await dump_db()
        await message.answer_document(document=open('csv/dump.tar.xz', 'rb'))
        # await message.answer_document(document=open('csv/calendar.csv', 'rb'))
        # await message.answer_document(document=open('csv/events.csv', 'rb'))
        # await message.answer_document(document=open('csv/students.csv', 'rb'))


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
        await message.answer('Example:\n/setup Иванов Иван Иванович')
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


@dp.message_handler(commands='start')
async def start_cmd(message: Message):
    if message.from_user.id == settings.ADMIN_ID:
        await bot.set_my_commands(commands_list)
    await message.answer(
        'For the first time you need to setup name via /setup\n'
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
    try:
        await message.delete()
    except MessageCantBeDeleted:
        pass
    await query.answer('Rolling back...')


@dp.callback_query_handler(text='apple')
async def apple(query: CallbackQuery):
    message = query.message
    await message.answer(
        text='Choose your IOS version: (PM me if you have IOS 13 and its different)',
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton('IOS 12', callback_data='ios12'),
            InlineKeyboardButton('IOS 14', callback_data='ios14')))
    try:
        await message.delete()
    except MessageCantBeDeleted:
        pass
    await query.answer('Rolling back...')


@dp.callback_query_handler(text='ios12')
async def ios12(query: CallbackQuery):
    message = query.message
    await message.answer_video(
        caption='How to import calendar to apple IOS 12 devices:',
        video=settings.GIF_IOS12,
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton('How to add?', callback_data='how_to')))
    try:
        await message.delete()
    except MessageCantBeDeleted:
        pass
    await query.answer('Rolling back...')


@dp.callback_query_handler(text='ios14')
async def ios14(query: CallbackQuery):
    message = query.message
    await message.answer_video(
        caption='How to import calendar to apple IOS 14 devices:',
        video=settings.GIF_IOS14,
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton('How to add?', callback_data='how_to')))
    try:
        await message.delete()
    except MessageCantBeDeleted:
        pass
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
    scheduler.add_job(parser, 'date', run_date=datetime.now(), args=[get_logger('worker')])
    dp.middleware.setup(LoggingMiddleware())
    scheduler.start()
    executor.start_polling(dp)
    scheduler.shutdown()
