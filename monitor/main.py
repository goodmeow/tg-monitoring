from __future__ import annotations

"""
Legacy entrypoint kept for backward compatibility.

Delegates to the new modular App under `tgbot`.
Prefer running: python -m tgbot.main
"""

import asyncio
from tgbot.domain.config import load_config
from tgbot.core.app import App


def main():
    cfg = load_config()
    asyncio.run(App(cfg).run())


if __name__ == "__main__":
    main()
