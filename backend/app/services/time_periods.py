"""
Shared date-period reader for the copilot.

Turns phrases like "today", "yesterday", "last 5 days", "this week", "last month"
into a concrete date range, so every copilot tool interprets time the same way.
"""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional, Any

MAX_PERIOD_DAYS = 365


@dataclass
class Period:
    start: date
    end: date
    label: str              # e.g. "Last 5 days", "Yesterday", "This week"
    explicit: bool = True   # False when no period was mentioned and the default was used

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    @property
    def start_str(self) -> str:
        return self.start.isoformat()

    @property
    def end_str(self) -> str:
        return self.end.isoformat()

    def contains(self, date_str: str) -> bool:
        """date_str is 'YYYY-MM-DD' (how sales dates are stored)."""
        return self.start_str <= (date_str or "") <= self.end_str

    def range_text(self) -> str:
        """Human-readable range, e.g. '26 Oct' or '24 Oct – 30 Oct'."""
        fmt = lambda d: f"{d.day} {d.strftime('%b')}"
        if self.start == self.end:
            return fmt(self.start)
        return f"{fmt(self.start)} – {fmt(self.end)}"

    def previous(self) -> "Period":
        """The period of the same length immediately before this one."""
        length = self.days
        prev_end = self.start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=length - 1)
        label = "day before" if length == 1 else f"previous {length} days"
        return Period(prev_start, prev_end, label)


def last_n_days(n: int, today: Optional[date] = None, explicit: bool = True) -> Period:
    today = today or date.today()
    n = max(1, min(int(n), MAX_PERIOD_DAYS))
    label = "Today" if n == 1 else f"Last {n} days"
    return Period(today - timedelta(days=n - 1), today, label, explicit)


def parse_period(text: Optional[str], default_days: int = 7, today: Optional[date] = None) -> Period:
    """
    Read a time period from free text. Supported:
      today, yesterday, this week, last/previous week, this month, last/previous month,
      last/past N days|weeks|months, "N days", "14d", week/weekly, month/monthly.
    Anything else -> the last `default_days` days (marked explicit=False).
    """
    today = today or date.today()
    q = (text or "").lower()

    if re.search(r"\btoday\b|\btonight\b", q):
        return Period(today, today, "Today")
    if re.search(r"\bday before yesterday\b", q):
        d = today - timedelta(days=2)
        return Period(d, d, "Day before yesterday")
    if re.search(r"\byesterday\b", q):
        d = today - timedelta(days=1)
        return Period(d, d, "Yesterday")

    # "last 5 days", "past 2 weeks", "3 months", "14d"
    m = re.search(r"\b(\d{1,3})\s*(d|days?|w|wks?|weeks?|m|mos?|months?)\b", q)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if unit.startswith("w"):
            n *= 7
        elif unit.startswith("m"):
            n *= 30
        if n >= 1:
            return last_n_days(n, today)

    if re.search(r"\b(last|previous|past)\s+week\b", q):
        this_monday = today - timedelta(days=today.weekday())
        start = this_monday - timedelta(days=7)
        return Period(start, start + timedelta(days=6), "Last week")
    if re.search(r"\bthis\s+week\b|\bweek\s+so\s+far\b", q):
        return Period(today - timedelta(days=today.weekday()), today, "This week")

    if re.search(r"\b(last|previous|past)\s+month\b", q):
        first_this_month = today.replace(day=1)
        last_prev = first_this_month - timedelta(days=1)
        return Period(last_prev.replace(day=1), last_prev, "Last month")
    if re.search(r"\bthis\s+month\b|\bmonth\s+so\s+far\b", q):
        return Period(today.replace(day=1), today, "This month")

    if re.search(r"\b(a|one|the)\s+week\b|\bweekly\b", q):
        return last_n_days(7, today)
    if re.search(r"\b(a|one|the)\s+month\b|\bmonthly\b", q):
        return last_n_days(30, today)
    if re.search(r"\bfortnight\b", q):
        return last_n_days(14, today)

    return last_n_days(default_days, today, explicit=False)


def period_from_args(args: dict, default_days: int = 7) -> Period:
    """
    Period from tool arguments (from Gemini or the keyword parser):
    a `period` phrase wins, then a `days` number, then the default.
    """
    phrase: Any = args.get("period")
    if isinstance(phrase, str) and phrase.strip():
        p = parse_period(phrase, default_days=default_days)
        if p.explicit:
            return p
    days = args.get("days")
    try:
        if days is not None and int(float(days)) >= 1:
            return last_n_days(int(float(days)))
    except (TypeError, ValueError):
        pass
    return last_n_days(default_days, explicit=False)
