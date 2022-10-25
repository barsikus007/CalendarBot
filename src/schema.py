from datetime import datetime
from pydantic import BaseModel, conlist


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
    moduleName: str | None
    categoryID: int | None
    moduleID: int | None
    # ID of event inside module (similar if same theme)
    moduleDisID: int | None
    theme: str
    aud: str | None
    link: str | None
    teacher: None
    teacherName: None
    teacherFullName: None
    teacherEmail: None
    teacherNumberMobile: None
    # https://example.com/photoP/{photoPath}
    photoPath: None
    teacherID: None
    # https://example.com/WebApp/#/PersonalKab/{userID}
    userID: None
    raspItemID: int
    # ID based on university timetable (1 - 7) (10 - custom)
    timeZanID: int
    teachersNames: str
    groupName: str
    groups: list[Group]
    teachers: list[Teacher]
    groupID: int
    type: str | None
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
    # frontend settings
    allowEdit: bool
    isRaspDisp: bool
    showExportButton: bool
    # list of schedule events
    raspList: list[Event]
    # idk
    userCategories: conlist(None, max_items=0)


class Response(BaseModel):
    # response data
    data: ResponseData | None
    # info message
    msg: str
    # state of success (-1, 1)
    state: int
