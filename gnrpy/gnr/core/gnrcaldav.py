# -*- coding: utf-8 -*-
"""gnrcaldav - CalDAV calendar integration (DEPRECATED).

.. deprecated::
    This module is deprecated and will be removed in a future version.
    Do not use ``gnr.core.gnrcaldav``.

This module provided CalDAV calendar integration using the caldav library.
It is no longer maintained and should not be used in new code.
"""

from __future__ import annotations

# REVIEW:DEAD — entire module is deprecated (line 1 raises DeprecationWarning)
raise DeprecationWarning(
    "Please don't using gnr.core.gnrcaldav module, deprecated. Will be removed soon"
)

# The code below is unreachable due to the raise above, but is preserved
# for reference during the deprecation period.

from datetime import datetime  # noqa: E402, F401
from typing import TYPE_CHECKING, Any  # noqa: E402, F401

import caldav  # noqa: E402, F401
from caldav.elements import dav  # noqa: E402, F401

from gnr.core.gnrbag import Bag, VObjectBag  # noqa: E402, F401
from gnr.core.gnrlang import getUuid  # noqa: E402, F401

if TYPE_CHECKING:
    from caldav import Calendar, DAVClient, Principal


def test() -> "CalDavConnection":  # pragma: no cover
    """Test function with hardcoded credentials (DO NOT USE).

    Returns:
        A CalDavConnection instance.

    Warning:
        Contains hardcoded credentials. For testing only.
    """
    # REVIEW:SECURITY — hardcoded credentials in source code
    return CalDavConnection(
        user="giovanni.porcari@softwell.it",
        password="toporaton",
        host="p04-caldav.icloud.com",
        root="/9403090/calendars/",
    )


def test1() -> "CalDavConnection":  # pragma: no cover
    """Test function for local CalDAV server.

    Returns:
        A CalDavConnection instance.
    """
    return CalDavConnection(
        user="gpo@localhost",
        password="",
        host="localhost",
        port=5232,
        root="/gpo/calendard",
        protocol="http",
    )


def testcal() -> Any:  # pragma: no cover
    """Test function to fetch calendar events.

    Returns:
        Event data from the first event in 'Personale' calendar.
    """
    s = test()
    personale = s.calendars["Personale"]
    events = personale.events()
    e0 = events[0]
    e0.load()
    data = e0.data
    return data


def dt(dt_val: datetime | str) -> str:
    """Convert datetime to iCalendar format string.

    Args:
        dt_val: A datetime object or string.

    Returns:
        The datetime formatted as iCalendar string (YYYYMMDDTHHMMSSz).
    """
    if isinstance(dt_val, datetime):
        return dt_val.strftime("%Y%m%dT%H%M%SZ")
    return dt_val  # type: ignore[return-value]


class CalDavConnection:
    """CalDAV server connection wrapper.

    Provides methods to connect to a CalDAV server and manage calendars
    and events.

    Args:
        host: CalDAV server hostname.
        user: Username for authentication.
        password: Password for authentication.
        root: Root path on the server.
        port: Server port. Defaults to 443.
        protocol: Protocol to use ('http' or 'https'). Defaults to 'https'.

    Attributes:
        host: Server hostname.
        port: Server port.
        user: Username.
        password: Password.
        root: Root path.
        protocol: Connection protocol.
        url: Full connection URL.
    """

    def __init__(
        self,
        host: str | None = None,
        user: str | None = None,
        password: str | None = None,
        root: str | None = None,
        port: int = 443,
        protocol: str = "https",
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.root = root or "/"
        self.protocol = protocol
        # REVIEW:SECURITY — password in URL is not secure
        self.url = (
            f"{self.protocol}://{self.user}:{self.password}@"
            f"{self.host}:{self.port}{self.root}"
        )

    @property
    def client(self) -> "DAVClient":
        """Lazily create and return the DAV client."""
        if not hasattr(self, "_client"):
            self._client: DAVClient = caldav.DAVClient(self.url)
        return self._client

    @property
    def principal(self) -> "Principal":
        """Lazily create and return the principal."""
        if not hasattr(self, "_principal"):
            self._principal: Principal = caldav.Principal(self.client, self.url)
        return self._principal

    @property
    def calendars(self) -> dict[str, "Calendar"]:
        """Lazily load and return calendars as a dict by name."""
        if not hasattr(self, "_calendars"):
            calendars = self.principal.calendars()
            self._calendars: dict[str, Calendar] = {}
            for calendar in calendars:
                p = calendar.get_properties([dav.DisplayName()])
                if p:
                    calname = p[dav.DisplayName().tag]
                    self._calendars[calname] = calendar
        return self._calendars

    def createEvent(
        self,
        uid: str | None = None,
        dtstamp: datetime | None = None,
        dtstart: datetime | str | None = None,
        dtend: datetime | str | None = None,
        summary: str | None = None,
        calendar: str | None = None,
    ) -> None:
        """Create a new calendar event.

        Args:
            uid: Unique identifier for the event. Auto-generated if not provided.
            dtstamp: Timestamp of event creation. Defaults to now.
            dtstart: Event start time.
            dtend: Event end time.
            summary: Event summary/title.
            calendar: Name of the calendar to add the event to.

        Raises:
            AssertionError: If the calendar is not found.
        """
        tpl = (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "PRODID:%(prodid)s\r\n"
            "BEGIN:VEVENT\r\n"
            "UID:%(uid)s\r\n"
            "DTSTAMP:%(dtstamp)s\r\n"
            "DTSTART:%(dtstart)s\r\n"
            "DTEND:%(dtend)s\r\n"
            "SUMMARY:%(summary)s\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR"
        )
        cal = self.calendars.get(calendar)  # type: ignore[arg-type]
        assert cal, "Missing calendar"
        data = tpl % dict(
            uid=uid or getUuid(),
            dtstamp=dt(dtstamp or datetime.now()),
            dtstart=dt(dtstart),  # type: ignore[arg-type]
            dtend=dt(dtend),  # type: ignore[arg-type]
            summary=summary,
            prodid="VCALENDAR genropy",
        )
        caldav.Event(self.client, data=data, parent=cal).save()

    def eventsBag(self, calendarName: str) -> Bag:
        """Get all events from a calendar as a Bag.

        Args:
            calendarName: Name of the calendar.

        Returns:
            A Bag containing all events from the calendar.
        """
        result = Bag()
        calendar = self.calendars.get(calendarName)
        if calendar:
            events = calendar.events()
            for event in events:
                event.load()
                data = VObjectBag(event.data)
                result.addItem("evento", data)
        return result


__all__ = ["CalDavConnection", "dt"]
