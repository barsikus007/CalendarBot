from sqlalchemy import Column, ForeignKey, Text, Integer, TIMESTAMP

from utils import Base


class Students(Base):
    __tablename__ = 'students'

    student_id = Column(Integer, primary_key=True, unique=True, nullable=False)
    fio = Column(Text, nullable=False)
    telegram_id = Column(Integer)
    calendar_id = Column(Text)

    def to_dict(self):
        fio = self.fio.split()
        return {
            'name': self.fio,
            'short_name': f'{fio[0]} {fio[1][0]}. {fio[2][0]}.',
            'student_id': self.student_id,
            'telegram_id': self.telegram_id,
            'calendar_id': self.calendar_id,
        }


class Events(Base):
    __tablename__ = 'events'

    rasp_item_id = Column(Integer, primary_key=True, unique=True, nullable=False)
    start = Column(TIMESTAMP(timezone=True), nullable=False)
    end = Column(TIMESTAMP(timezone=True), nullable=False)
    name = Column(Text, nullable=False)
    color = Column(Text)
    aud = Column(Text)
    link = Column(Text)
    teacher = Column(Text)
    module_name = Column(Text)
    theme = Column(Text)
    group_name = Column(Text)
    description = Column(Text)
    hash = Column(Text)

    def to_dict(self) -> dict:
        return {
            'start': self.start,
            'end': self.end,
            'name': self.name,
            'description': self.description,
            'aud': self.aud
        }


class Calendar(Base):
    __tablename__ = 'calendar'

    # TODO ondelete='CASCADE'
    student_id = Column(ForeignKey('students.student_id'), primary_key=True, nullable=False)
    rasp_item_id = Column(ForeignKey('events.rasp_item_id'), primary_key=True, nullable=False)
    hash = Column(Text, nullable=False)
