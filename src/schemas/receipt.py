"""
Pydantic schemas shared across tools and agents.

Keeping this in one place means the OCR/extraction agent, the sheets
tool, and the tests all validate against the exact same contract.
"""
from __future__ import annotations

from datetime import date as Date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class LineItem(BaseModel):
    name: str
    quantity: float = 1.0
    unit_price: Optional[float] = None
    total_price: Optional[float] = None


class StructuredReceipt(BaseModel):
    receipt_id: str = Field(..., description="Stable id, usually derived from source message")
    merchant_name: str
    date: Date
    total_amount: float
    tax_amount: float = 0.0
    currency: str = "INR"
    payment_method: str = "unknown"
    items: list[LineItem] = Field(default_factory=list)
    category: str = "Uncategorized"
    source_chat_id: Optional[str] = None
    source_message_id: Optional[str] = None
    content_hash: Optional[str] = Field(
        default=None,
        description="Hash of the source image bytes, used for idempotency dedupe",
    )

    @field_validator("total_amount", "tax_amount")
    @classmethod
    def _must_be_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("amount fields must be non-negative")
        return v

    @field_validator("currency")
    @classmethod
    def _currency_upper(cls, v: str) -> str:
        return v.upper()


DEFAULT_CATEGORIES = [
    "Food",
    "Travel",
    "Office Supplies",
    "Utilities",
    "Entertainment",
    "Health",
    "Groceries",
    "Uncategorized",
]

SHEET_COLUMNS = [
    "receipt_id",
    "date",
    "merchant_name",
    "category",
    "total_amount",
    "tax_amount",
    "currency",
    "payment_method",
    "items_summary",
    "source_chat_id",
    "content_hash",
    "processed_at",
]
