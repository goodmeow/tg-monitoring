import os
import asyncio

os.environ.setdefault('ENV_FILE', '.env.example')
os.environ.setdefault('MODULES', 'monitoring,rss')

from monitor.config import load_config
from tgbot.core.app import App


async def main():
    cfg = load_config()
    app = App(cfg)
    await app._start_modules()
    await asyncio.sleep(1.0)
    await app._stop_modules()
    print('SMOKE_OK')


if __name__ == '__main__':
    asyncio.run(main())

