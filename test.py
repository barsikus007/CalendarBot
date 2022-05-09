import asyncio

from worker import get_calendar_from_site


async def main():
    get_calendar_from_site(200000)


if __name__ == '__main__':
    import platform

    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
