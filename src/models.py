from datetime import datetime

from pydantic import EmailStr
from sqlmodel import SQLModel, Field


__all__ = ['Student', 'Event', 'Calendar']


class Student(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True, nullable=False)
    fio: str
    telegram_id: int | None
    calendar_id: EmailStr | None


class Event(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True, nullable=False)
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


class Calendar(SQLModel, table=True):
    student_id: int | None = Field(
        default=None, foreign_key='student.id', primary_key=True, nullable=False
    )
    event_id: int | None = Field(
        default=None, foreign_key='event.id', primary_key=True, nullable=False
    )
    hash: str
