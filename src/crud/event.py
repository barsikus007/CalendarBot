from sqlalchemy import update

from src.db import async_session
from src.models import Event


async def get_event(event_id: int) -> Event | None:
    async with async_session() as session:
        return await session.get(Event, event_id)


async def create_event(event: Event):
    async with async_session() as session:
        session.add(event)
        await session.commit()


async def update_event(event: Event):
    async with async_session() as session:
        q = update(Event).where(Event.id == event.id)
        q = q.values(**event.dict()).execution_options(synchronize_session="fetch")
        await session.exec(q)
        await session.commit()
