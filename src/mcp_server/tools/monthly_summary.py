"""Tool: get_monthly_summary"""
from __future__ import annotations

import calendar
import logging
from collections import defaultdict

from src.integrations.google_sheets_client import fetch_rows_for_month
from src.integrations.llm_provider import summarize_month

logger = logging.getLogger("receipto.tools.monthly_summary")


def get_monthly_summary(month: int, year: int, user_id: str | None = None) -> dict:
    """
    Aggregate a month's worth of expense rows by category and merchant.

    Args:
        month: 1-12
        year: e.g. 2026
        user_id: optional filter (reserved for multi-user setups)

    Returns:
        {
          category_totals: {category: total},
          top_merchants: [[merchant, total], ...],
          total_spend: float,
          summary_text: str,
          row_count: int,
        }
    """
    rows = fetch_rows_for_month(month, year)

    category_totals: dict[str, float] = defaultdict(float)
    merchant_totals: dict[str, float] = defaultdict(float)
    total_spend = 0.0

    for row in rows:
        try:
            amount = float(row.get("total_amount", 0) or 0)
        except (TypeError, ValueError):
            continue
        category_totals[row.get("category", "Uncategorized")] += amount
        merchant_totals[row.get("merchant_name", "Unknown")] += amount
        total_spend += amount

    top_merchants = sorted(merchant_totals.items(), key=lambda kv: kv[1], reverse=True)
    month_label = f"{calendar.month_name[month]} {year}"

    summary_text = summarize_month(dict(category_totals), top_merchants, total_spend, month_label)

    return {
        "month_label": month_label,
        "category_totals": dict(category_totals),
        "top_merchants": top_merchants,
        "total_spend": round(total_spend, 2),
        "summary_text": summary_text,
        "row_count": len(rows),
    }
