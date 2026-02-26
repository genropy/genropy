# -*- coding: utf-8 -*-
"""gnrdatetime - Timezone-aware datetime utilities.

This module provides timezone-aware datetime handling with sensible defaults.
It offers a drop-in replacement for the standard ``datetime`` module that
ensures all datetime objects are timezone-aware (UTC by default).

The main class :class:`TZDateTime` extends ``datetime.datetime`` with
factories that always return aware datetimes.

Example:
    >>> from gnr.core.gnrdatetime import datetime
    >>> now = datetime.now()  # Returns UTC-aware datetime
    >>> from gnr.core.gnrdatetime import now as adesso
    >>> adesso()  # Alternative functional interface
"""

from __future__ import annotations

import datetime as _dt
from typing import Self


class TZDateTime(_dt.datetime):
    """A datetime subclass whose factories return timezone-aware datetimes.

    Goals:
        - Always return aware datetimes (UTC by default).
        - Public factories (.now/.utcnow/.fromiso) yield standard datetime, not TZDateTime.
        - Keep call sites unchanged: ``from gnr.core.gnrdatetime import datetime``.

    Note:
        The factories return standard ``datetime.datetime`` objects, not
        ``TZDateTime`` instances, to prevent the subclass from leaking
        into user code.
    """

    @classmethod
    def now(cls, tz: _dt.tzinfo | None = None) -> _dt.datetime:
        """Return an aware datetime (UTC by default) as a standard datetime.

        Args:
            tz: Timezone to use. Defaults to UTC if not specified.

        Returns:
            A timezone-aware datetime object.
        """
        tz = tz or _dt.timezone.utc
        return _dt.datetime.now(tz)

    @classmethod
    def utcnow(cls) -> _dt.datetime:
        """Return an aware UTC datetime as a standard datetime.

        Returns:
            A UTC timezone-aware datetime object.

        Note:
            Unlike the deprecated ``datetime.datetime.utcnow()``, this method
            returns an aware datetime with UTC timezone info.
        """
        return _dt.datetime.now(_dt.timezone.utc)

    @classmethod
    def fromiso(
        cls,
        iso_str: str,
        tz: _dt.tzinfo | None = None,
    ) -> _dt.datetime:
        """Parse an ISO 8601 datetime string.

        If the parsed datetime is naive, attaches the specified timezone
        (default UTC). If aware, converts to the specified timezone if
        provided, otherwise keeps the original timezone.

        Args:
            iso_str: An ISO 8601 formatted datetime string.
            tz: Timezone to apply or convert to. Defaults to UTC for naive datetimes.

        Returns:
            A timezone-aware datetime object.

        Example:
            >>> TZDateTime.fromiso("2024-01-15T10:30:00")
            datetime.datetime(2024, 1, 15, 10, 30, tzinfo=datetime.timezone.utc)
        """
        dt = _dt.datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=(tz or _dt.timezone.utc))
        return dt.astimezone(tz or dt.tzinfo)

    def __new__(
        cls,
        *args: int,
        tz: _dt.tzinfo | None = None,
        **kwargs: int | _dt.tzinfo | None,
    ) -> Self:
        """Construct a TZDateTime ensuring timezone info is set.

        Allows ``TZDateTime(...)`` to behave like ``datetime.datetime(...)``
        but ensures tzinfo is set (defaults to UTC).

        Args:
            *args: Positional arguments for datetime (year, month, day, etc.).
            tz: Timezone to apply if not specified in kwargs.
            **kwargs: Keyword arguments for datetime.

        Returns:
            A timezone-aware datetime object.
        """
        tz = tz or _dt.timezone.utc
        base = _dt.datetime.__new__(cls, *args, **kwargs)
        if base.tzinfo is None:
            base = base.replace(tzinfo=tz)
        return base  # type: ignore[return-value]


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


def now(tz: _dt.tzinfo | None = None) -> _dt.datetime:
    """Return an aware datetime (UTC by default).

    Module-level helper that can be imported directly.

    Args:
        tz: Timezone to use. Defaults to UTC if not specified.

    Returns:
        A timezone-aware datetime object.

    Example:
        >>> from gnr.core.gnrdatetime import now as adesso
        >>> adesso()
    """
    return TZDateTime.now(tz)


def utcnow() -> _dt.datetime:
    """Return an aware UTC datetime.

    Module-level helper that can be imported directly.

    Returns:
        A UTC timezone-aware datetime object.
    """
    return TZDateTime.utcnow()


__all__ = [
    # Classes / constants
    "TZDateTime",
    # datetime-like surface
    "datetime",
    "date",
    "time",
    "timedelta",
    "timezone",
    "tzinfo",
    "MINYEAR",
    "MAXYEAR",
    # helpers
    "now",
    "utcnow",
]
