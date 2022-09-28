import asyncio
from aiogram import Bot
from aiogram.types import User, Message, Chat
from main import setup
from src.settings import settings


async def main():
    bot = Bot(token=settings.TELEGRAM_TOKEN)

    fake_message = Message()
    fake_message.message_id = 1337
    fake_message.from_user = User()
    fake_message.from_user.id = settings.ADMIN_ID
    fake_message.chat = Chat()
    fake_message.chat.id = settings.ADMIN_ID
    fake_message.text = "/start"
    print(fake_message.text.split())
    Bot.set_current(bot)
    await setup(fake_message)
    await bot.session.close()


if __name__ == '__main__':
    import platform

    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
