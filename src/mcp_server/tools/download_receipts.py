"""Tool: download_new_receipts"""
from __future__ import annotations

from src.integrations import telegram_client
from src.config import settings


def download_new_receipts(source: str = "telegram", since_timestamp: float | None = None) -> list[dict]:
    """
    Fetch new receipt messages (images/PDFs) from the configured source
    and download them locally.

    Args:
        source: "telegram" or "whatsapp"
        since_timestamp: unix timestamp; only messages newer than this are returned

    Returns:
        list of {receipt_id, chat_id, message_id, file_path}
    """
    if source == "telegram":
        receipts = telegram_client.fetch_new_receipt_messages(since_timestamp)
        return [r.__dict__ for r in receipts]

    if source == "whatsapp":
        if not settings.whatsapp_enabled:
            return []
        # Optional extension point: implement WhatsApp Cloud API polling/
        # webhook ingestion here, mirroring the Telegram shape above.
        raise NotImplementedError("WhatsApp ingestion is a stubbed optional extension")

    raise ValueError(f"Unknown source: {source}")
