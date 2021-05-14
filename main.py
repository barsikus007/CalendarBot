import os
import pickle
import base64
import logging
from datetime import datetime, timezone

import ujson as json
import aiohttp
import requests
from aiogram import md, Bot, Dispatcher, types, executor
from googleapiclient import errors
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


from config import TOKEN, adminID

"""
Unofficial donstux bot by @ogu_rez
To start type /start
"""


creds = None
if os.path.exists(f'token.pickle'):
    with open(f'token.pickle', 'rb') as token:
        creds = pickle.load(token)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', ['https://www.googleapis.com/auth/calendar'])
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open(f'token.pickle', 'wb') as token:
        pickle.dump(creds, token)
service = build('calendar', 'v3', credentials=creds)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
commands = [
    types.BotCommand(command="/start", description="Start the Bot"),
    types.BotCommand(command="/help", description="Help page about commands"),
    types.BotCommand(command="/guide", description="Quick video how to use bot"),
    types.BotCommand(command="/change_lang", description="Change language"),
    types.BotCommand(command="/setup", description="Choose groups for calendar"),
    types.BotCommand(command="/get", description="Generate personal calendar url and link"),
    types.BotCommand(command="/get_aud", description="Get events by aud"),
    types.BotCommand(command="/remove", description="Remove calendar (import this file to remove all imported events)"),
]


def log(message: types.Message = None, query: types.CallbackQuery = None):
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


###
def converter(calendar_json):
    ics_json = []
    for event in calendar_json:
        event_dict = dict()
        start = datetime.strptime(event["start"], "%Y-%m-%dT%H:%M:%S+03:00").astimezone(timezone.utc)
        end = datetime.strptime(event["end"], "%Y-%m-%dT%H:%M:%S+03:00").astimezone(timezone.utc)
        event_dict["Subject"] = event["name"]
        event_dict["Start"] = start.strftime("%Y%m%dT%H%M%SZ")
        event_dict["End"] = end.strftime("%Y%m%dT%H%M%SZ")
        description_raw = event["info"]
        description = f"""Преподаватель: {description_raw['teacher']}
Модуль: {description_raw['moduleName']}
Тема: {description_raw['theme']}
Группа: {description_raw['groupName']}"""
        event_dict["Description"] = description.replace("\n", r"\n")
        event_dict["Location"] = description_raw["aud"]
        event_dict["groupName"] = description_raw["groupName"]
        event_dict["hash"] = event["raspItemsIDs"][0]
        ics_json.append(event_dict)
    return ics_json


async def hash_check(ics_json):
    hash_sum = sum([event["hash"] for event in ics_json])
    if hash_sum == 0:
        await bot.send_message(chat_id=adminID, text=f"AHTUNG BROKEN: {hash_sum}")
        print(f"\n{hash_sum}")


def rm_generator(ics_json):
    hash_sum = sum([event["hash"] for event in ics_json])
    ics_file = f"Calendars/Remover-{hash_sum}.ics"
    with open(ics_file, "w", encoding="utf-8") as file:
        file.write(f"""BEGIN:VCALENDAR
PRODID:DonstuX Bot
VERSION:2.0\n""")
        for event in ics_json:
            file.write(f"""BEGIN:VEVENT
DTSTART:{event["Start"]}
DTEND:{event["End"]}
UID:{event["hash"]}@google.com
SUMMARY:{event["Subject"]}
DESCRIPTION:{event["Description"]}
LOCATION:{event["Location"]}
METHOD:CANCEL
STATUS:CANCELLED
END:VEVENT\n""")
        file.write("END:VCALENDAR")
    print("U")
    return ics_file


async def rm_calendar(student_id):
    print(student_id)
    print("P", end="")
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
            async with session.get(f"https://edu.donstu.ru/api/RaspManager?studentID={student_id}") as response:
                calendar_json = await response.json()
        calendar_json = calendar_json["data"]["raspList"]
    except Exception as e:
        await bot.send_message(chat_id=adminID, text=f"AHTUNG EXCEPTION:\n{type(e)}\n{e}")
        print(type(e))
        print(e)
        return "error"

    print("C", end="")
    ics_json = converter(calendar_json)

    print("H", end="")
    await hash_check(ics_json)

    print("G", end="")
    return rm_generator(ics_json)
###


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
async def errors(event: types.Update = None, exception: BaseException = None):
    await report(f"{event}\n{type(exception)}\n{exception}")


@dp.message_handler(commands="dump")
async def dump(message: types.Message):
    print(log(message))
    if message.from_user.id == adminID:
        await message.answer_document(document=open("database.pickle", "rb"))
        await message.answer_document(document=open("calendars.pickle", "rb"))


@dp.message_handler()
async def anal_plug(message: types.Message):
    return await message.answer('Closed for maintenance')


@dp.message_handler(commands="setup")
async def setup(message: types.Message):
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


@dp.message_handler(commands="remove")
async def remove(message: types.Message):
    print(log(message))
    tg_id = message.from_user.id
    user_data = get_info(tg_id)
    if user_data:
        document = await rm_calendar(student_id=user_data["uid"])
        if document == "error":
            await message.answer("Server error - try again later or contact @ogu_rez for local copy of calendar")
            return
        await message.answer_document(
            caption=f"Ok here is your remover:\n"
                    f"https://calendar.google.com/calendar/r/settings/export",
            document=open(document, "rb"))
        await message.answer_video(
            caption=f"Here is mobile guide\n"
                    f"If you are PC user, you need to do same",
            video="BAACAgIAAxkBAAIB2V9RcaqM8iaA7cXF2ol7d3hw3NMaAALXBgACV9yRSooP4Eino0rrGwQ")
    else:
        await message.answer("Please type /setup first!")


@dp.message_handler(commands="get")
async def get(message: types.Message):
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
        reply_markup=types.InlineKeyboardMarkup().row(
            types.InlineKeyboardButton("How to add?", callback_data="how_to")))


@dp.message_handler(commands="get_aud")
async def get_aud(message: types.Message):
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
async def help_cmd(message: types.Message):
    print(log(message))
    await message.answer(
        f"/setup\n"
        f"/get"
    )


@dp.message_handler(commands="guide")
async def guide(message: types.Message):
    print(log(message))
    await message.answer_video(caption="Take it!",
                               video="BAACAgIAAxkBAAILJ19zIf-u66UuT4iPXZgMYpsNaNp3AAKQCAACmKGhS4GiuulwDSSfGwQ")


@dp.message_handler(commands="start")
async def start_cmd(message: types.Message):
    print(log(message))
    await bot.set_my_commands(commands)
    await message.answer("For the first time you need to setup name via /setup\n"
                         "After than you can get calendar link via /get\n"
                         "To remove previous calendar use /remove\n"
                         "To show full guide type /guide")


@dp.callback_query_handler(text="google")
async def google(query: types.CallbackQuery):
    print(log(query=query))
    message = query.message
    await message.answer_video(
        caption="Here is guide how to import calendar to normal devices:\n"
                "https://calendar.google.com/calendar/r/settings/addcalendar",
        video="BAACAgIAAxkBAAILI19zITUx2Y63QZaESS2J6ZzPvXAFAAKOCAACmKGhS0H3HEyivX0-GwQ")
    await query.answer(f"Here you go!")


@dp.callback_query_handler(text="apple")
async def apple(query: types.CallbackQuery):
    print(log(query=query))
    message = query.message
    await message.answer(
        text="Choose your IOS version: (PM me if you have IOS 13)",
        reply_markup=types.InlineKeyboardMarkup().row(
            types.InlineKeyboardButton("IOS 12", callback_data="ios12"),
            types.InlineKeyboardButton("IOS 14", callback_data="ios14")))
    await message.delete()
    await query.answer(f"Here you go!")


@dp.callback_query_handler(text="ios12")
async def ios12(query: types.CallbackQuery):
    print(log(query=query))
    message = query.message
    await message.answer_video(
        caption="Here is guide how to import calendar to apple IOS 12 devices:",
        video="BAACAgIAAxkBAAIPQl_MG0MKEhfFftbuoriC5mbbWBv9AAK2CgACp_VhSvfYLTSvrUeuHgQ",
        reply_markup=types.InlineKeyboardMarkup().row(
            types.InlineKeyboardButton("How to add?", callback_data="how_to")))
    await message.delete()
    await query.answer(f"Here you go!")


@dp.callback_query_handler(text="ios14")
async def ios14(query: types.CallbackQuery):
    print(log(query=query))
    message = query.message
    await message.answer_video(
        caption="Here is guide how to import calendar to apple IOS 14 devices:",
        video="BAACAgIAAxkBAAIPIV_MDyqvQ5l4aVuFNvW9v-kEYLC_AAKjCgACrhnpSZbHuSG9ZSOLHgQ",
        reply_markup=types.InlineKeyboardMarkup().row(
            types.InlineKeyboardButton("How to add?", callback_data="how_to")))
    await message.delete()
    await query.answer(f"Here you go!")


@dp.callback_query_handler(text="how_to")
async def how_to_er(query: types.CallbackQuery):
    print(log(query=query))
    message = query.message
    await message.answer(
        text="Choose your platform:",
        reply_markup=types.InlineKeyboardMarkup().row(
            types.InlineKeyboardButton("Apple", callback_data="apple"),
            types.InlineKeyboardButton("Other", callback_data="google")))
    await query.answer(f"Here you go!")


@dp.message_handler(content_types=types.ContentTypes.ANY)
async def all_other_messages(message: types.Message):
    print(log(message))
    await message.answer("Type /start")


if __name__ == "__main__":
    executor.start_polling(dp)
