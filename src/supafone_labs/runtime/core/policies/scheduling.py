from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

from supafone_labs.runtime.core.decision import RuntimeDecision


def normalize_relative_window(raw_text: str, *, today: date) -> tuple[date, date] | None:
    text = " ".join((raw_text or "").strip().lower().split())
    if not text:
        return None

    weekday = today.weekday()
    monday_this_week = today - timedelta(days=weekday)
    friday_this_week = monday_this_week + timedelta(days=4)

    if text == "this week":
        return today, max(today, friday_this_week)
    if text == "later this week":
        start = today + timedelta(days=1)
        if start > friday_this_week:
            start = today
        return start, max(start, friday_this_week)
    if text == "next week":
        start = monday_this_week + timedelta(days=7)
        return start, start + timedelta(days=4)
    if text == "this month":
        end = date(today.year, today.month, monthrange(today.year, today.month)[1])
        return today, end
    if text == "next month":
        if today.month == 12:
            year = today.year + 1
            month = 1
        else:
            year = today.year
            month = today.month + 1
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        return start, end
    return None


class DateNormalizationPolicy:
    def normalize(self, raw_text: str, *, today: date) -> RuntimeDecision | None:
        resolved = normalize_relative_window(raw_text, today=today)
        if resolved is None:
            return None
        return RuntimeDecision.request_availability_window(
            raw_text=raw_text,
            normalized_start=resolved[0].isoformat(),
            normalized_end=resolved[1].isoformat(),
        )
