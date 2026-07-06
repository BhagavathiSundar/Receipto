"""
Central configuration loader.

All secrets and environment-specific values come from environment variables
(loaded from `.env` via python-dotenv in local dev; injected directly by the
platform in production/Docker). Nothing here is hard-coded.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()  # no-op in production if no .env file is present


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    # Telegram
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_mode: str = os.getenv("TELEGRAM_MODE", "polling")
    telegram_webhook_url: str = os.getenv("TELEGRAM_WEBHOOK_URL", "")
    telegram_webhook_secret: str = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")

    # WhatsApp
    whatsapp_enabled: bool = field(default_factory=lambda: _bool("WHATSAPP_ENABLED"))
    whatsapp_access_token: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    whatsapp_phone_number_id: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

    # OCR
    ocr_provider: str = os.getenv("OCR_PROVIDER", "tesseract")
    google_vision_api_key: str = os.getenv("GOOGLE_VISION_API_KEY", "")

    # LLM
    llm_provider: str = os.getenv("LLM_PROVIDER", "anthropic")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Google Sheets
    sheets_spreadsheet_id: str = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")
    sheets_tab_name: str = os.getenv("GOOGLE_SHEETS_TAB_NAME", "Expenses")
    google_application_credentials: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

    # Storage
    receipt_storage_dir: str = os.getenv("RECEIPT_STORAGE_DIR", "./data/receipts_tmp")
    receipt_retention_hours: int = int(os.getenv("RECEIPT_RETENTION_HOURS", "24"))

    # App
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    default_timezone: str = os.getenv("DEFAULT_USER_TIMEZONE", "Asia/Kolkata")
    default_currency: str = os.getenv("DEFAULT_CURRENCY", "INR")

    # MCP
    mcp_host: str = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    mcp_port: int = int(os.getenv("MCP_SERVER_PORT", "8765"))


settings = Settings()
