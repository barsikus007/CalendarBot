from datetime import datetime

from pydantic import EmailStr
from sqlmodel import SQLModel, Field


__all__ = ['Student', 'Event', 'Calendar']


class Student(SQLModel, table=True):  # student_id, nullable=False
    id: int | None = Field(default=None, primary_key=True)
    fio: str
    telegram_id: int | None
    calendar_id: EmailStr | None


class Event(SQLModel, table=True):  # rasp_item_id, nullable=False
    id: int | None = Field(default=None, primary_key=True)
    name = str
    color: str
    start = datetime
    end = datetime
    aud: str | None
    link: str | None
    teachers: str | None  # +s
    module_name: str
    theme: str
    group_names: str  # +s
    description: str
    hash: str


class Calendar(SQLModel, table=True):  # nullable=False
    student_id: int | None = Field(
        default=None, foreign_key='students.id', primary_key=True
    )
    event_id: int | None = Field(  # rasp_item_id
        default=None, foreign_key='events.id', primary_key=True
    )
    hash: str
