from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, InlineQuery, Message


class RequestLogMiddleware(BaseMiddleware):
    def __init__(self, logger):
        self.log = logger

    async def __call__(
        self,
        handler: Callable[[Any, dict], Awaitable[Any]],
        event: Any,
        data: dict,
    ) -> Any:
        try:
            if isinstance(event, Message):
                chat_id = event.chat.id if event.chat else None
                user_id = event.from_user.id if event.from_user else None
                text = event.text or ""
                command = text.split()[0] if text.startswith("/") else None
                self.log.info(
                    "request_received type=message chat_id=%s user_id=%s command=%s",
                    chat_id,
                    user_id,
                    command,
                )
            elif isinstance(event, CallbackQuery):
                chat_id = (
                    event.message.chat.id
                    if event.message and event.message.chat
                    else None
                )
                user_id = event.from_user.id if event.from_user else None
                self.log.info(
                    "request_received type=callback_query chat_id=%s user_id=%s",
                    chat_id,
                    user_id,
                )
            elif isinstance(event, InlineQuery):
                user_id = event.from_user.id if event.from_user else None
                self.log.info("request_received type=inline_query user_id=%s", user_id)
        except Exception:
            self.log.debug("request log failed", exc_info=True)
        return await handler(event, data)
