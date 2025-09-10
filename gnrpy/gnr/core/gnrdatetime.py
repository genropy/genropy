# gnr/core/gnrdatetime.py

import datetime as _dt

# ZoneInfo: stdlib from 3.9+, backport for 3.8
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:  # Python 3.8
    from backports.zoneinfo import ZoneInfo  # pip install backports.zoneinfo

# Reuse a single UTC instance
UTC = ZoneInfo("UTC")


class TZDateTime(_dt.datetime):
    """
    Helper class whose factories return standard timezone-aware datetimes.
    Goals:
      - Always return aware datetimes (UTC by default).
      - Public factories (.now/.utcnow/.fromiso) yield _dt.datetime, not TZDateTime.
      - Keep call sites unchanged: `from gnr.core.gnrdatetime import datetime; datetime.now()`.
    """

    # ---- Factories (return standard datetime) ----
    @classmethod
    def now(cls, tz=None):
        """Return an aware datetime (UTC by default) as a standard _dt.datetime."""
        tz = tz or UTC
        return _dt.datetime.now(tz)

    @classmethod
    def utcnow(cls):
        """Return an aware UTC datetime as a standard _dt.datetime."""
        return _dt.datetime.now(UTC)

    @classmethod
    def fromiso(cls, iso_str, tz=None):
        """
        Parse ISO 8601. If naive, attach tz (default UTC). If aware, convert to tz if provided.
        Always returns a standard _dt.datetime.
        """
        dt = _dt.datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=(tz or UTC))
        return dt.astimezone(tz or dt.tzinfo)

    # ---- Constructor bridge ----
    def __new__(cls, *args, **kwargs):
        """
        Allow `TZDateTime(...)` to behave like _dt.datetime(...) but ensure tzinfo.
        Returns a standard _dt.datetime (not the subclass) to prevent leaking TZDateTime.
        """
        tz = kwargs.pop("tz", None) or UTC
        base = _dt.datetime.__new__(cls, *args, **kwargs)
        if base.tzinfo is None:
            base = base.replace(tzinfo=tz)
        return base  # standard datetime object


# ---- Public surface mirroring `datetime` where useful ----
# Drop-in compatibility for:
#   from gnr.core.gnrdatetime import datetime
#   now = datetime.now()
datetime = TZDateTime

# Forward common symbols to ease migration away from `from datetime import ...`
date = _dt.date
time = _dt.time
timedelta = _dt.timedelta
timezone = _dt.timezone
tzinfo = _dt.tzinfo
MINYEAR = _dt.MINYEAR
MAXYEAR = _dt.MAXYEAR


# Flat helpers: importable as functions (e.g., `from ... import now as adesso`)
def now(tz=None):
    """Module-level helper: aware now (UTC by default), standard datetime."""
    return TZDateTime.now(tz)


def utcnow():
    """Module-level helper: aware UTC now, standard datetime."""
    return TZDateTime.utcnow()


__all__ = [
    # Classes / constants
    "TZDateTime", "ZoneInfo", "UTC",
    # datetime-like surface
    "datetime", "date", "time", "timedelta", "timezone", "tzinfo",
    "MINYEAR", "MAXYEAR",
    # helpers
    "now", "utcnow",
]