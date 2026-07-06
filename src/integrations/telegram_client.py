"""
Thin Telegram wrapper used by the download_new_receipts and
send_notification tools. Uses python-telegram-bot under the hood.

Only handles: (1) pulling new photo/document messages, (2) downloading
files locally, (3) sending text messages back. Nothing else.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

from src.config import settings
from src.security.redaction import safe_log_payload

logger = logging.getLogger("receipto.telegram")


@dataclass
class IncomingReceipt:
    receipt_id: str
    chat_id: str
    message_id: str
    file_path: str


def _bot():
    try:
        from telegram import Bot
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("python-telegram-bot not installed") from exc
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    return Bot(token=settings.telegram_bot_token)


def fetch_new_receipt_messages(since_timestamp: float | None = None) -> list[IncomingReceipt]:
    """
    Poll Telegram for new photo/document updates and download them to
    RECEIPT_STORAGE_DIR. Returns a list of IncomingReceipt records.

    In webhook mode, this function is not used directly; the webhook
    handler (see main.py) pushes updates in as they arrive instead.
    """
    import asyncio

    async def _poll():
        bot = _bot()
        updates = await bot.get_updates(timeout=5)
        results: list[IncomingReceipt] = []
        storage_dir = Path(settings.receipt_storage_dir)
        storage_dir.mkdir(parents=True, exist_ok=True)

        for update in updates:
            message = update.message
            if message is None:
                continue
            if since_timestamp and message.date.timestamp() < since_timestamp:
                continue

            file_obj = None
            if message.photo:
                file_obj = await message.photo[-1].get_file()
            elif message.document:
                file_obj = await message.document.get_file()
            else:
                continue

            receipt_id = f"tg-{message.chat_id}-{message.message_id}"
            local_path = storage_dir / f"{receipt_id}{Path(file_obj.file_path).suffix or '.jpg'}"
            await file_obj.download_to_drive(custom_path=str(local_path))

            logger.info("Downloaded receipt %s", safe_log_payload({"receipt_id": receipt_id}))
            results.append(
                IncomingReceipt(
                    receipt_id=receipt_id,
                    chat_id=str(message.chat_id),
                    message_id=str(message.message_id),
                    file_path=str(local_path),
                )
            )
        return results

    return asyncio.run(_poll())


def send_message(chat_id: str, text: str) -> None:
    import asyncio

    async def _send():
        bot = _bot()
        await bot.send_message(chat_id=chat_id, text=text)

    asyncio.run(_send())
    logger.info("Sent notification to chat %s", chat_id)
