from typing import List, Dict, Union, Optional

from sqlalchemy import update, delete
from sqlalchemy.future import select
from sqlalchemy.orm import Session

from models import Students, Events, Calendar


class StudentsDAL:
    def __init__(self, session: Session):
        self.session = session

    async def create_students(self, students_list: List[List[Union[int, str]]]):
        students_ids = [_[0] for _ in students_list]
        for student in students_list:
            if len(student[1].split()) != 3:
                print(f'Student {student[0]} - {student[1]} have error in their name\nFix it manually!')
            await self.session.merge(Students(student_id=student[0], fio=student[1]))
        await self.session.execute(
            delete(Students).where(Students.student_id.notin_(students_ids))
        )

    async def create_student(self, student_id: int, fio: str):
        new_student = Students(student_id=student_id, fio=fio)
        self.session.add(new_student)
        await self.session.flush()

    async def update_student(
            self,
            student_id: Optional[int] = None,
            fio: Optional[str] = None,
            telegram_id: Optional[int] = None,
            calendar_id: Optional[int] = None
    ):
        if student_id is not None:
            q = update(Students).where(Students.student_id == student_id)
        elif fio is not None:
            q = update(Students).where(Students.fio == fio)
        else:
            raise ValueError('student_id or fio is not specified')
        if telegram_id:
            q = q.values(telegram_id=telegram_id)
        if calendar_id:
            q = q.values(calendar_id=calendar_id)
        q.execution_options(synchronize_session="fetch")
        await self.session.execute(q)

    async def get_students(self) -> List[Students]:
        q = await self.session.execute(
            select(Students).order_by(Students.student_id)
        )
        return q.scalars().all()

    async def _get_calendar_id(self, student_id: int) -> Students.calendar_id:
        q = await self.session.execute(
            select(Students).where(Students.student_id == student_id)
        )
        return q.scalars().first()

    async def get_calendars(self) -> List[Students]:
        q = await self.session.execute(
            select(Students).where(Students.calendar_id.isnot(None)).order_by(Students.student_id)
        )
        return q.scalars().all()


class EventsDAL:
    def __init__(self, session: Session):
        self.session = session

    async def create_event(self, event: Dict[str, Union[int, str]]):
        new_event = Events(**event)
        self.session.add(new_event)
        await self.session.flush()

    async def update_event(self, event: Dict[str, Union[int, str]]):
        q = update(Events).where(Events.rasp_item_id == event['rasp_item_id'])
        q = q.values(**event)
        q.execution_options(synchronize_session="fetch")
        await self.session.execute(q)

    async def get_event_by_id(self, rasp_item_id: int):
        q = await self.session.execute(
            select(Events).where(Events.rasp_item_id == rasp_item_id)
        )
        return q.scalars().first()


class CalendarDAL:
    def __init__(self, session: Session):
        self.session = session

    async def create_calendar(self, student_id: int, rasp_item_id: int, event_hash: str):
        new_calendar = Calendar(student_id=student_id, rasp_item_id=rasp_item_id, hash=event_hash)
        self.session.add(new_calendar)
        await self.session.flush()

    async def update_calendar(self, student_id: int, rasp_item_id: int, event_hash: str):
        q = update(Calendar).where(
            Calendar.student_id == student_id, Calendar.rasp_item_id == rasp_item_id
        )
        q = q.values(hash=event_hash)
        q.execution_options(synchronize_session="fetch")
        await self.session.execute(q)

    async def delete_calendar(self, student_id: int, rasp_item_id: int):
        await self.session.execute(
            delete(Calendar).where(
                Calendar.student_id == student_id and Calendar.rasp_item_id == rasp_item_id
            )
        )

    async def get_calendar(self, student_id: int) -> List[Calendar]:
        q = await self.session.execute(
            select(Calendar).where(Calendar.student_id == student_id)
        )
        return q.scalars().all()

    async def get_calendar_hash(self, student_id: int) -> List[Calendar]:
        q = await self.session.execute(
            select(Calendar.hash).where(Calendar.student_id == student_id)
        )
        return q.scalars().all()
