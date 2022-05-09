from datetime import datetime

from pydantic import EmailStr
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, TIMESTAMP


__all__ = ['Student', 'Event', 'Calendar']


class Student(SQLModel, table=True):
    id: int = Field(primary_key=True)
    fio: str
    telegram_id: int | None
    calendar_id: EmailStr | None


class Event(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str
    color: str
    start: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True), nullable=False))
    end: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True), nullable=False))
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
