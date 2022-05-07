import asyncio
from datetime import datetime
from pydantic import BaseModel, ValidationError, conlist

from db import get_calendars
from worker import get_calendar_from_site


class Group(BaseModel):
    name: str
    groupID: int
    raspItemID: None


class Teacher(BaseModel):
    fullName: str
    name: str
    email: str | None
    number: None
    userID: int | None
    teacherID: int
    raspItemID: None


class EventInfo(BaseModel):
    moduleName: str
    categoryID: int | None
    moduleID: int | None
    moduleDisID: int | None
    theme: str
    aud: str | None
    link: str | None
    teacher: None
    teacherName: None
    teacherFullName: None
    teacherEmail: None
    teacherNumberMobile: None
    photoPath: None
    teacherID: None
    userID: None
    raspItemID: int
    timeZanID: int
    teachersNames: str
    groupName: str
    groups: list[Group]
    teachers: list[Teacher]
    groupID: int
    typeID: int | None
    studentsCount: int
    course: int
    courses: list


class Event(BaseModel):
    name: str
    color: str
    bordered: bool
    start: datetime
    end: datetime
    info: EventInfo
    groupsIDs: list[int]
    teachersIDs: list[int | None]
    raspItemsIDs: list[int]


class ResponseData(BaseModel):
    allowEdit: bool
    isRaspDisp: bool
    raspList: list[Event]
    showExportButton: bool
    userCategories: conlist(None, max_items=0)


class Response(BaseModel):
    data: ResponseData
    msg: str
    state: int


async def validate():
    calendars = await get_calendars()
    for student in calendars:
        print(student.student_id)
        rasp: list[dict] = get_calendar_from_site(student.student_id)
        for e in rasp:
            try:
                Event(**e)
            except ValidationError as ee:
                print(ee)
                print(e)


if __name__ == '__main__':
    import platform

    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(validate())
