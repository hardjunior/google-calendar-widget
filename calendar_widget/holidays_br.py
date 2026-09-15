"""Brazilian holidays detection module."""

import datetime
from typing import Optional

import holidays


def get_brazilian_holidays(year: int) -> dict[datetime.date, str]:
    """Get all Brazilian holidays for a given year.

    Returns a dict mapping date -> holiday name.
    """
    br_holidays = holidays.Brazil(years=year)
    return {date: name for date, name in br_holidays.items()}


def is_holiday(date: datetime.date) -> bool:
    """Check if a given date is a Brazilian holiday."""
    br_holidays = holidays.Brazil(years=date.year)
    return date in br_holidays


def get_holiday_name(date: datetime.date) -> Optional[str]:
    """Get the holiday name for a given date, or None."""
    br_holidays = holidays.Brazil(years=date.year)
    return br_holidays.get(date)


def is_weekend(date: datetime.date) -> bool:
    """Check if a given date is a weekend (Saturday or Sunday)."""
    return date.weekday() >= 5
