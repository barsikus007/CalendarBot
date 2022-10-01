import asyncio
from aiogram import Bot
from aiogram.types import User, Message, Chat
from main import setup, setup_id, setup_auth
from src.settings import settings


async def main():
    target_id = settings.ADMIN_ID
    bot = Bot(token=settings.TELEGRAM_TOKEN)

    fake_message = Message()
    fake_message.message_id = 1337
    fake_message.from_user = User()
    fake_message.from_user.id = target_id
    fake_message.chat = Chat()
    fake_message.chat.id = target_id
    fake_message.text = "/start"
    print(fake_message.text.split())
    Bot.set_current(bot)
    await setup(fake_message)
    # await setup_id(fake_message)
    # await setup_auth(fake_message)
    await bot.session.close()


if __name__ == '__main__':
    import platform

    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
