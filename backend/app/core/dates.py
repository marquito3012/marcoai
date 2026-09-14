"""Date/time helpers that depend only on the standard library."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def local_day_bounds_utc(day: date, user_tz: ZoneInfo) -> tuple[datetime, datetime]:
    """(start, end) UTC boundaries covering the *local* day `day` for `user_tz`.

    Interprets `day` as local wall time, so the returned window spans from
    local 00:00 to the following local 00:00 regardless of UTC offset or DST.
    """
    start_local = datetime(day.year, day.month, day.day, tzinfo=user_tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)
