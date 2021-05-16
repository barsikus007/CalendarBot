import os
import pickle
import base64
import logging
from datetime import datetime

import ujson as json
import aiohttp
from aiogram import md, executor, Bot, Dispatcher
from aiogram.types import Update, Message, BotCommand, ContentTypes, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from googleapiclient import errors


from worker import get_service
from config import TOKEN, adminID

"""
Unofficial donstux bot by @ogu_rez
To start type /start
"""


service = get_service()
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
commands = [
    BotCommand(command="/start", description="Start the Bot"),
    BotCommand(command="/help", description="Help page about commands"),
    BotCommand(command="/guide", description="Quick video how to use bot"),
    BotCommand(command="/change_lang", description="Change language"),
    BotCommand(command="/setup", description="Choose groups for calendar"),
    BotCommand(command="/get", description="Generate personal calendar url and link"),
    BotCommand(command="/get_aud", description="Get events by aud"),
]


def log(message: Message = None, query: CallbackQuery = None):
    if message:
        return f"{datetime.now().strftime('[%H:%M:%S]')} " \
               f"[{message.from_user.id}/{message.from_user.mention}]: {message.text}"
    if query:
        return f"{datetime.now().strftime('[%H:%M:%S]')} " \
               f"[{query.from_user.id}/{query.from_user.mention}]: {query.data}"


async def report(text):
    await bot.send_message(chat_id=adminID, text=text, disable_notification=True)


def get_id(fio):
    with open("Students.json", "rb") as f:
        students_list = json.load(f)["data"]["allStudent"]
        for student in students_list:
            if student["fullName"] == fio:
                return student


def get_aud_id(aud_name):
    with open("auds.pickle", "rb") as f:
        auds = pickle.load(f)["data"]
    for aud in auds:
        if aud["name"] == aud_name:
            return aud["id"]


def get_info(tg_id):
    with open("database.pickle", "rb") as f:
        return pickle.load(f).get(tg_id, False)


def dump_info(tg_id, uid):
    with open("database.pickle", "rb") as f:
        users_data = pickle.load(f)
    if not users_data.get(tg_id, False):
        users_data[tg_id] = dict()
    users_data[tg_id]["uid"] = uid
    with open("database.pickle", "wb") as f:
        pickle.dump(users_data, f)


def get_name(user_id):
    with open("Students.json", "rb") as f:
        students_list = json.load(f)["data"]["allStudent"]
        for student in students_list:
            if student["studentID"] == user_id:
                return student["fio"]


def create_calendar(user_id):
    print("Creating new calendar...")
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
    service.acl().insert(calendarId=created_calendar["id"], body=rule).execute()
    with open("calendars.pickle", "rb") as f:
        calendars = pickle.load(f)
    calendars[user_id] = created_calendar['id']
    with open("calendars.pickle", "wb") as f:
        pickle.dump(calendars, f)
    print("SUCCESS")
    return created_calendar["id"]


async def get_calendar_link(user_id):
    with open("calendars.pickle", "rb") as f:
        calendar_link = pickle.load(f).get(user_id, False)
    if not calendar_link:
        calendar_link = create_calendar(user_id)
    else:
        try:
            print("Calendar link exist")
            service.calendars().get(calendarId=calendar_link).execute()
        except errors.HttpError as e:
            if e.resp.status == 404:
                print(f"No calendar with that link... Strange\n{calendar_link}\n{user_id}")
                await bot.send_message(chat_id=adminID, text="AHTUNG, 404 ERROR")
                calendar_link = create_calendar(user_id)
            else:
                return
    print(calendar_link)
    return calendar_link


@dp.errors_handler()
async def errors(event: Update = None, exception: BaseException = None):
    await report(f"{event}\n{type(exception)}\n{exception}")


@dp.message_handler(commands="dump")
async def dump(message: Message):
    print(log(message))
    if message.from_user.id == adminID:
        await message.answer_document(document=open("database.pickle", "rb"))
        await message.answer_document(document=open("calendars.pickle", "rb"))


@dp.message_handler()
async def anal_plug(message: Message):
    return await message.answer('Closed for maintenance')


@dp.message_handler(commands="setup")
async def setup(message: Message):
    print(log(message))
    splitted = message.text.split()
    if message.text == "/setup Иванов Иван Иванович":
        await message.answer("Genius ( ͡° ͜ʖ ͡°)")
        return
    if len(splitted) == 1:
        await message.answer(f"Example:\n/setup Иванов Иван Иванович")
    elif len(splitted) < 4:
        await message.answer(f"Wrong input:\n{message.text}\nExample:\n/setup Иванов Иван Иванович")
    else:
        student = get_id(" ".join(splitted[1:]))
        print(student)
        if student:
            dump_info(
                tg_id=message.from_user.id,
                uid=student["studentID"])
            await get(message)
        else:
            await message.answer(f"Wrong name:\n{message.text}\nExample:\n/setup Иванов Иван Иванович")


@dp.message_handler(commands="get")
async def get(message: Message):
    print(log(message))
    tg_id = message.from_user.id
    user_data = get_info(tg_id)
    if not user_data:
        await message.answer("Please type /setup first!")
        return
    user_id = user_data["uid"]
    await message.answer("Generating your link...")
    calendar_link = await get_calendar_link(user_id)
    if not calendar_link:
        await message.answer("Server error - try again later or contact @ogu_rez for report problem")
        return
    base64_link = base64.b64encode(calendar_link.encode('ascii')).decode('ascii').replace('=', '')
    calendar_url = f"https://calendar.google.com/calendar/u/0?cid={base64_link}"
    await message.answer(
        text=f"Ok here is your Google Calendar id:\n"
             f"{calendar_link}\n"
             f"It will be filled within 15 minutes\n"
             f"\n"
             f"If you are PC user use calendar link instead:\n"
             f"{calendar_url}\n"
             f"If you are APPLE user import ics file instead:\n"
             f"https://calendar.google.com/calendar/ical/{calendar_link.split('@')[0]}%40group.calendar.google.com/public/basic.ics",
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton("How to add?", callback_data="how_to")))


@dp.message_handler(commands="get_aud")
async def get_aud(message: Message):
    print(log(message))
    if message.text == "/get_aud 8-612":
        await message.answer("Genius ( ͡° ͜ʖ ͡°)")
        return
    date = datetime.now().strftime("%Y-%m-%d")
    aud_id = get_aud_id(message.text.split()[-1])
    if aud_id:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
                async with session.get(f"https://edu.donstu.ru/api/Rasp?idAudLine={aud_id}&sdate={date}") as response:
                    events = await response.json()
            text = f"Classes in {message.text.split()[-1]} at {datetime.now().strftime('%d.%m.%Y')}:\n\n"
            if events["data"] is None:
                await message.answer(
                    f"No classes in {message.text.split()[-1]} at {datetime.now().strftime('%d.%m.%Y')}")
                return
            for event in events["data"]["rasp"]:
                event_date = event['дата'][:10]
                if event_date == date:
                    time_str = event['часы'].replace("-", ":").replace("\n", " ").split()
                    text += f"FROM {time_str[0]} TO {time_str[1]}\n" \
                            f"Class {event['дисциплина']}\n" \
                            f"Teacher {event['преподаватель']}\n" \
                            f"Group {event['группа']}\n\n"
        except Exception as e:
            await bot.send_message(chat_id=adminID, text=f"AHTUNG EXCEPTION:\n{type(e)}\n{e}")
            print(type(e))
            print(e)
            await message.answer("Server error")
            return
        await message.answer(text)
    else:
        await message.answer(f"Wrong auditory\n{message.text}\nExample:\n/get_aud 8-612")


@dp.message_handler(commands="help")
async def help_cmd(message: Message):
    print(log(message))
    await message.answer(
        f"/setup\n"
        f"/get"
    )


@dp.message_handler(commands="guide")
async def guide(message: Message):
    print(log(message))
    await message.answer_video(caption="Take it!",
                               video="BAACAgIAAxkBAAILJ19zIf-u66UuT4iPXZgMYpsNaNp3AAKQCAACmKGhS4GiuulwDSSfGwQ")


@dp.message_handler(commands="start")
async def start_cmd(message: Message):
    print(log(message))
    await bot.set_my_commands(commands)
    await message.answer("For the first time you need to setup name via /setup\n"
                         "After than you can get calendar link via /get\n"
                         "To remove previous calendar use /remove\n"
                         "To show full guide type /guide")


@dp.callback_query_handler(text="google")
async def google(query: CallbackQuery):
    print(log(query=query))
    message = query.message
    await message.answer_video(
        caption="Here is guide how to import calendar to normal devices:\n"
                "https://calendar.google.com/calendar/r/settings/addcalendar",
        video="BAACAgIAAxkBAAILI19zITUx2Y63QZaESS2J6ZzPvXAFAAKOCAACmKGhS0H3HEyivX0-GwQ")
    await query.answer(f"Here you go!")


@dp.callback_query_handler(text="apple")
async def apple(query: CallbackQuery):
    print(log(query=query))
    message = query.message
    await message.answer(
        text="Choose your IOS version: (PM me if you have IOS 13)",
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton("IOS 12", callback_data="ios12"),
            InlineKeyboardButton("IOS 14", callback_data="ios14")))
    await message.delete()
    await query.answer(f"Here you go!")


@dp.callback_query_handler(text="ios12")
async def ios12(query: CallbackQuery):
    print(log(query=query))
    message = query.message
    await message.answer_video(
        caption="Here is guide how to import calendar to apple IOS 12 devices:",
        video="BAACAgIAAxkBAAIPQl_MG0MKEhfFftbuoriC5mbbWBv9AAK2CgACp_VhSvfYLTSvrUeuHgQ",
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton("How to add?", callback_data="how_to")))
    await message.delete()
    await query.answer(f"Here you go!")


@dp.callback_query_handler(text="ios14")
async def ios14(query: CallbackQuery):
    print(log(query=query))
    message = query.message
    await message.answer_video(
        caption="Here is guide how to import calendar to apple IOS 14 devices:",
        video="BAACAgIAAxkBAAIPIV_MDyqvQ5l4aVuFNvW9v-kEYLC_AAKjCgACrhnpSZbHuSG9ZSOLHgQ",
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton("How to add?", callback_data="how_to")))
    await message.delete()
    await query.answer(f"Here you go!")


@dp.callback_query_handler(text="how_to")
async def how_to_er(query: CallbackQuery):
    print(log(query=query))
    message = query.message
    await message.answer(
        text="Choose your platform:",
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton("Apple", callback_data="apple"),
            InlineKeyboardButton("Other", callback_data="google")))
    await query.answer(f"Here you go!")


@dp.message_handler(content_types=ContentTypes.ANY)
async def all_other_messages(message: Message):
    print(log(message))
    await message.answer("Type /start")


if __name__ == "__main__":
    executor.start_polling(dp)
