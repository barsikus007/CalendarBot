from datetime import datetime

from pydantic import EmailStr
from sqlmodel import SQLModel, Field, Column, ForeignKey, TIMESTAMP, BigInteger


__all__ = ['Student', 'Event', 'Calendar']


class Student(SQLModel, table=True):
    id: int = Field(primary_key=True)
    fio: str
    telegram_id: int | None = None
    calendar_id: EmailStr | None = None


class Event(SQLModel, table=True):
    id: int = Field(sa_column=Column(BigInteger(), primary_key=True))
    start: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True), nullable=False))
    end: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True), nullable=False))
    name: str
    color: str
    aud: str
    link: str | None
    group_names: str
    description: str
    hash: str


class Calendar(SQLModel, table=True):
    student_id: int | None = Field(
        foreign_key='student.id', primary_key=True, nullable=False
    )
    event_id: int | None = Field(
        sa_column=Column(BigInteger(), ForeignKey(Event.id), primary_key=True, nullable=False),
    )
    hash: str
