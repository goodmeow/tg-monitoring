from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.types import InputSticker


def _pack_name(user_id: int, bot_username: str, suffix: str | None = None) -> str:
    base = f"u{user_id}_by_{bot_username}"
    if suffix:
        return f"{base}_{suffix}"
    return base


def _sticker_format_from_message(msg: Message) -> Optional[str]:
    st = msg.sticker
    if not st:
        return None
    try:
        if getattr(st, "is_video", False):
            return "video"
        if getattr(st, "is_animated", False):
            return "animated"
        return "static"
    except Exception:
        return None


@dataclass
class StickerKangService:
    def build_router(self) -> Router:
        router = Router()

        @router.message(Command("kang"))
        async def cmd_kang(message: Message):
            if not message.reply_to_message or not (
                message.reply_to_message.sticker or message.reply_to_message.photo
            ):
                await message.answer("Reply ke sticker (atau gambar) dengan /kang")
                return

            # Only implement sticker-to-set for now (no photo conversion)
            if not message.reply_to_message.sticker:
                await message.answer("Saat ini hanya mendukung kang dari sticker. Kirim sticker dan reply dengan /kang.")
                return

            st = message.reply_to_message.sticker
            emoji = (st.emoji or "🙂").strip()[:2]

            bot = message.bot
            me = await bot.get_me()
            if not me.username:
                await message.answer("Bot tidak punya username; tidak bisa membuat sticker set.")
                return

            user_id = message.from_user.id
            # Allow optional pack suffix: /kang <suffix>
            parts = (message.text or "").split(maxsplit=1)
            suffix = parts[1].strip() if len(parts) > 1 else None
            name = _pack_name(user_id, me.username, suffix)
            title = f"{message.from_user.first_name}'s pack"

            fmt = _sticker_format_from_message(message.reply_to_message) or "static"
            input_sticker = InputSticker(sticker=st.file_id, emoji_list=[emoji])

            # Try add to existing set, else create new then add
            exists = False
            try:
                await bot.get_sticker_set(name=name)
                exists = True
            except Exception:
                exists = False

            try:
                if not exists:
                    # New unified API first
                    try:
                        await bot.create_new_sticker_set(
                            user_id=user_id,
                            name=name,
                            title=title,
                            stickers=[input_sticker],
                            sticker_format=fmt,
                        )
                    except Exception:
                        # Fallback older API (static/animated/video specific fields)
                        if fmt == "animated":
                            await bot.create_new_sticker_set(
                                user_id=user_id,
                                name=name,
                                title=title,
                                tgs_sticker=st.file_id,
                                emojis=emoji,
                            )
                        elif fmt == "video":
                            await bot.create_new_sticker_set(
                                user_id=user_id,
                                name=name,
                                title=title,
                                webm_sticker=st.file_id,
                                emojis=emoji,
                            )
                        else:
                            await bot.create_new_sticker_set(
                                user_id=user_id,
                                name=name,
                                title=title,
                                png_sticker=st.file_id,
                                emojis=emoji,
                            )
                else:
                    try:
                        await bot.add_sticker_to_set(
                            user_id=user_id, name=name, sticker=input_sticker
                        )
                    except Exception:
                        # Fallback older API
                        if fmt == "animated":
                            await bot.add_sticker_to_set(
                                user_id=user_id,
                                name=name,
                                tgs_sticker=st.file_id,
                                emojis=emoji,
                            )
                        elif fmt == "video":
                            await bot.add_sticker_to_set(
                                user_id=user_id,
                                name=name,
                                webm_sticker=st.file_id,
                                emojis=emoji,
                            )
                        else:
                            await bot.add_sticker_to_set(
                                user_id=user_id,
                                name=name,
                                png_sticker=st.file_id,
                                emojis=emoji,
                            )
            except Exception as e:
                txt = str(e)
                if "bot was blocked" in txt.lower() or "start" in txt.lower():
                    await message.answer(
                        "Gagal: kamu harus /start bot di PM dulu agar bot bisa membuat sticker set untukmu."
                    )
                else:
                    await message.answer(f"Gagal menambahkan sticker: {e}")
                return

            link = f"https://t.me/addstickers/{name}"
            await message.answer(f"Done! Ditambahkan ke set kamu:\n{link}")

        return router

