"""
LLM provider abstraction used for:
  - structured extraction of receipt fields from noisy OCR text
  - expense categorization
  - natural-language monthly summary text

Provider is chosen via LLM_PROVIDER (anthropic | openai). Both paths are
expected to return **JSON only** for the extraction call, which callers
parse defensively (see extract_receipt.py tool).
"""
from __future__ import annotations

import json

from src.config import settings

EXTRACTION_SYSTEM_PROMPT = """You are a receipt-parsing engine. Given noisy OCR
text from a purchase receipt, extract structured fields and respond with
ONLY a JSON object (no markdown fences, no commentary) matching this shape:

{
  "merchant_name": string,
  "date": "YYYY-MM-DD",
  "total_amount": number,
  "tax_amount": number,
  "currency": string (ISO 4217, e.g. "INR", "USD"),
  "payment_method": string,
  "items": [{"name": string, "quantity": number, "unit_price": number, "total_price": number}],
  "category": one of ["Food","Travel","Office Supplies","Utilities","Entertainment","Health","Groceries","Uncategorized"]
}

If a field is not present in the text, make your best reasonable estimate;
never fabricate implausible values. Amounts must be non-negative numbers.
"""


def extract_structured_fields(raw_text: str, hints: str | None = None) -> dict:
    provider = settings.llm_provider.lower()
    user_prompt = raw_text if not hints else f"{raw_text}\n\nHints: {hints}"
    if provider == "mock":
        return _extract_with_mock(raw_text)
    if provider == "anthropic":
        return _extract_with_anthropic(user_prompt)
    if provider == "openai":
        return _extract_with_openai(user_prompt)
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


def _extract_with_mock(raw_text: str) -> dict:
    """
    Demo/test provider: naive regex-based field extraction so the pipeline
    runs fully offline (no API key required). Good enough for the sample
    fixtures in tests/fixtures and scripts/simulate_e2e.py - not intended
    as a real extraction strategy.
    """
    import re

    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    merchant = lines[0] if lines else "Unknown Merchant"

    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", raw_text)
    date_str = date_match.group(1) if date_match else None

    # \b prevents "Subtotal:" from matching before the real "Total:" line
    total_match = re.search(r"(?i)\btotal[:\s]+\$?([\d,]+\.\d{2})", raw_text)
    total = float(total_match.group(1).replace(",", "")) if total_match else 0.0

    tax_match = re.search(r"(?i)tax[:\s]+\$?([\d,]+\.\d{2})", raw_text)
    tax = float(tax_match.group(1).replace(",", "")) if tax_match else 0.0

    currency_match = re.search(r"(?i)\b(inr|usd|eur|gbp)\b", raw_text)
    currency = currency_match.group(1).upper() if currency_match else "INR"

    payment_match = re.search(r"(?i)(cash|credit card|debit card|upi|card)", raw_text)
    payment_method = payment_match.group(1).title() if payment_match else "unknown"

    category = "Uncategorized"
    lowered = raw_text.lower()
    if any(k in lowered for k in ("restaurant", "cafe", "food", "diner")):
        category = "Food"
    elif any(k in lowered for k in ("uber", "taxi", "flight", "airlines", "train")):
        category = "Travel"
    elif any(k in lowered for k in ("stationery", "office", "supplies")):
        category = "Office Supplies"
    elif any(k in lowered for k in ("grocery", "supermarket", "mart")):
        category = "Groceries"

    return {
        "merchant_name": merchant,
        "date": date_str or "2026-01-01",
        "total_amount": total,
        "tax_amount": tax,
        "currency": currency,
        "payment_method": payment_method,
        "items": [],
        "category": category,
    }


def _extract_with_anthropic(user_prompt: str) -> dict:
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("anthropic package not installed") from exc

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1000,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return _parse_json_response(text)


def _extract_with_openai(user_prompt: str) -> dict:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("openai package not installed") from exc

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    text = response.choices[0].message.content or ""
    return _parse_json_response(text)


def _parse_json_response(text: str) -> dict:
    cleaned = text.strip().strip("`")
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM did not return valid JSON: {text[:200]}...") from exc


def summarize_month(category_totals: dict, top_merchants: list, total_spend: float, month_label: str) -> str:
    """Generate a short natural-language summary. Falls back to a templated
    string if no LLM is configured, so the demo never hard-depends on an
    external API call for this step."""
    lines = [f"Spending summary for {month_label}: total {total_spend:.2f}."]
    if category_totals:
        top_cat = max(category_totals, key=category_totals.get)
        lines.append(f"Biggest category: {top_cat} ({category_totals[top_cat]:.2f}).")
    if top_merchants:
        lines.append("Top merchants: " + ", ".join(m for m, _ in top_merchants[:3]) + ".")
    return " ".join(lines)
