# gnr/core/gnrdatetime.py
import datetime as _dt
from typing import Optional
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")

class TZDateTime(_dt.datetime):
    """Helper per produrre datetime standard sempre timezone-aware (UTC di default)."""

    @classmethod
    def now(cls, tz: Optional[ZoneInfo] = None) -> _dt.datetime:
        tz = tz or UTC
        return _dt.datetime.now(tz)

    @classmethod
    def utcnow(cls) -> _dt.datetime:
        return _dt.datetime.now(UTC)

    @classmethod
    def fromiso(cls, iso_str: str, tz: Optional[ZoneInfo] = None) -> _dt.datetime:
        dt = _dt.datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=(tz or UTC))
        return dt.astimezone(tz or dt.tzinfo)

    def __new__(cls, *args, tz: Optional[ZoneInfo] = None, **kwargs) -> _dt.datetime:
        tz = tz or UTC
        dt = _dt.datetime.__new__(cls, *args, **kwargs)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        # converti subito in datetime puro
        return dt

# Export compatibili con datetime
datetime = TZDateTime
date = _dt.date
time = _dt.time
timedelta = _dt.timedelta
timezone = _dt.timezone
tzinfo = _dt.tzinfo
ZoneInfo = ZoneInfo
MINYEAR = _dt.MINYEAR
MAXYEAR = _dt.MAXYEAR

__all__ = [
    "datetime", "date", "time", "timedelta", "timezone", "tzinfo",
    "ZoneInfo", "TZDateTime", "UTC", "MINYEAR", "MAXYEAR",
]