import os
import asyncio
from aiogram import Bot
from tgbot.domain.config import load_config


async def main():
    cfg = load_config()
    bot = Bot(cfg.bot_token)
    me = await bot.get_me()
    print('GET_ME_OK', me.username)
    try:
        await bot.send_message(cfg.chat_id, '✅ Bot live-check: online (modular skeleton)')
        print('PING_SENT')
    except Exception as e:
        print('PING_FAIL', e)
    await bot.session.close()


if __name__ == '__main__':
    os.environ.setdefault('ENV_FILE', '.env')
    asyncio.run(main())

