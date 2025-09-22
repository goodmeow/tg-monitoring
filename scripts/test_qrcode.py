#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from types import SimpleNamespace

os.environ.setdefault("PYTHONPATH", ".")

from tgbot.services.qrcode_service import _render_qr_png, _normalize_text, QrCodeService
from tgbot.domain.config import Config


def main():
    text = " ".join(sys.argv[1:]) or "hello world"

    # Test normalize helper
    msg_direct = SimpleNamespace(text=f"/qrcode {text}", reply_to_message=None)
    msg_reply = SimpleNamespace(text="/qrcode", reply_to_message=SimpleNamespace(text=text, caption=None))
    print("normalize direct:", _normalize_text(msg_direct))
    print("normalize reply  :", _normalize_text(msg_reply))

    # Render QR PNG
    buf = _render_qr_png(text)
    outdir = "logs"
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, "qrcode_test.png")
    with open(outpath, "wb") as f:
        f.write(buf.getvalue())
    print("wrote:", outpath, "bytes:", os.path.getsize(outpath))

    # Build router to ensure handler wiring doesn't raise
    cfg = Config(bot_token="x", chat_id="123")
    svc = QrCodeService(cfg)
    router = svc.build_router()
    print("router ok, name:", router.name)


if __name__ == "__main__":
    main()

