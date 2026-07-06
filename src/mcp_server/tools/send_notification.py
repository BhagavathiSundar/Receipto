"""Tool: send_notification"""
from __future__ import annotations

import logging
import re

from src.integrations import telegram_client

logger = logging.getLogger("receipto.tools.send_notification")

# Very small guard against control characters / obvious injection payloads
# in message text before it goes out over the Bot API.
_UNSAFE_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def send_notification(chat_id: str, message_text: str, source: str = "telegram") -> dict:
    """
    Send a text message back to the user (confirmation or summary).

    Args:
        chat_id: destination chat id
        message_text: plain text body
        source: "telegram" or "whatsapp"

    Returns:
        {sent: bool}
    """
    if not chat_id or not isinstance(chat_id, str):
        raise ValueError("chat_id must be a non-empty string")
    clean_text = _UNSAFE_CONTROL_CHARS.sub("", message_text)[:4000]

    if source == "telegram":
        telegram_client.send_message(chat_id, clean_text)
        return {"sent": True}

    raise NotImplementedError(f"send_notification not implemented for source={source}")
