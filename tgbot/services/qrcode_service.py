# This file is part of tg-monitoring.
#
# tg-monitoring is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tg-monitoring is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tg-monitoring. If not, see <https://www.gnu.org/licenses/>.
#
# Author: Claude (Anthropic AI Assistant)
# Co-author: goodmeow (Harun Al Rasyid) <aarunalr@pm.me>

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import List

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile

from tgbot.domain.config import Config
from tgbot.vendor.qrcodegen import QrCode  # type: ignore

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("Pillow is required for QR code generation") from exc


def _is_allowed(chat_id: int | str, allowed_list: List[int | str]) -> bool:
    for allowed in allowed_list:
        if isinstance(allowed, int) and chat_id == allowed:
            return True
        if isinstance(allowed, str) and str(chat_id) == allowed:
            return True
    return False


def _normalize_text(message: Message) -> str | None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) >= 2:
        return parts[1].strip()
    if message.reply_to_message and (message.reply_to_message.text or message.reply_to_message.caption):
        return (message.reply_to_message.text or message.reply_to_message.caption or "").strip()
    return None


def _render_qr_png(payload: str, scale: int = 8, border: int = 4) -> io.BytesIO:
    qr = QrCode.encode_text(payload, QrCode.Ecc.MEDIUM)
    size = qr.get_size()
    dim = (size + border * 2) * scale
    img = Image.new("RGB", (dim, dim), "white")
    pixels = img.load()

    for y in range(size):
        for x in range(size):
            if qr.get_module(x, y):
                px = (x + border) * scale
                py = (y + border) * scale
                for dy in range(scale):
                    for dx in range(scale):
                        pixels[px + dx, py + dy] = (0, 0, 0)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


@dataclass
class QrCodeService:
    cfg: Config
    log: logging.Logger = logging.getLogger("tgbot.qrcode")

    def build_router(self) -> Router:
        router = Router()

        @router.message(Command("qrcode"))
        async def cmd_qrcode(message: Message):
            chat_id = message.chat.id
            if not _is_allowed(chat_id, self.cfg.allowed_chat_ids):
                return

            text = _normalize_text(message)
            if not text:
                await message.answer(
                    "Usage: /qrcode <text>\n"
                    "You can also reply to a message and send /qrcode to convert its text."
                )
                return
            if len(text) > 1024:
                await message.answer("Text too long (max 1024 characters).")
                return

            try:
                png = _render_qr_png(text)
            except Exception:
                self.log.exception("Failed to render QR code")
                await message.answer("Failed to generate QR code")
                return

            filename = "qrcode.png"
            await message.answer_photo(
                BufferedInputFile(png.getvalue(), filename=filename),
                caption="Here you go ✨",
            )

        return router
