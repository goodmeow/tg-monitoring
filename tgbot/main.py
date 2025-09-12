from __future__ import annotations

import asyncio

from monitor.config import load_config
from tgbot.core.app import App


def main():
    cfg = load_config()
    asyncio.run(App(cfg).run())


if __name__ == "__main__":
    main()

