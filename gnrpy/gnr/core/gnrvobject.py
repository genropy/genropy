# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy core - see LICENSE for details
# module gnrvobject : vCard and vCal object handling
# Copyright (c) : 2004 - 2007 Softwell sas - Milano
# Written by    : Jeff Edwards
# --------------------------------------------------------------------------
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
"""gnrvobject - vCard and vCal object handling.

This module provides classes for dealing with vCard objects using the
vobject library.

References:
    - http://hypercontent.sourceforge.net/docs/manual/develop/vcard.html
    - http://vobject.skyhouseconsulting.com/epydoc/

vCard Tag Reference:
    ========== =================== =============================================
    Name       Description         Semantic
    ========== =================== =============================================
    N          Name                Structured name representation
    FN         Formatted Name      Formatted name string
    NICKNAME   Nickname            Descriptive or familiar name
    PHOTO      Photograph          Image of the individual
    BDAY       Birthday            Date of birth
    ADR        Delivery Address    Physical delivery address
    LABEL      Label Address       Addressing label for delivery
    TEL        Telephone           Telephone number
    EMAIL      Email               Email address
    MAILER     Email Program       Type of email program (optional)
    TZ         Time Zone           Standard time zone information
    GEO        Global Positioning  Latitude and longitude
    TITLE      Title               Job title or position
    ROLE       Role                Role or occupation
    LOGO       Logo                Organization logo image
    AGENT      Agent               Information about representative
    ORG        Organization        Organization name/unit
    NOTE       Note                Supplemental information
    REV        Last Revision       Last update timestamp
    SOUND      Sound               Pronunciation of name
    URL        URL                 Internet location
    UID        Unique Identifier   Globally unique identifier
    VERSION    Version             vCard specification version
    KEY        Public Key          Public encryption key
    ========== =================== =============================================
"""

from __future__ import annotations

from typing import Any

import vobject

from gnr.core import logger

#: Valid vCard tag names (lowercase)
VALID_VCARD_TAGS: list[str] = [
    "n",
    "fn",
    "nickname",
    "photo",
    "bday",
    "adr",
    "label",
    "tel",
    "email",
    "mailer",
    "tz",
    "geo",
    "title",
    "role",
    "logo",
    "agent",
    "org",
    "note",
    "rev",
    "sound",
    "url",
    "uid",
    "version",
    "key",
]


class VCard:
    """A vCard object builder using the vobject library.

    Provides a wrapper around vobject.vCard() with helper methods
    for setting structured fields like name and address.

    Args:
        card: Optional dictionary of vCard data to populate.
        **kwargs: Additional vCard fields as keyword arguments.

    Attributes:
        j: The underlying vobject.vCard instance.

    Example:
        >>> card = VCard(fn={'#0': 'John Doe'}, email={'#0': 'john@example.com'})
        >>> print(card.doserialize())
    """

    def __init__(self, card: dict[str, Any] | None = None, **kwargs: Any) -> None:
        self.j = vobject.vCard()

        card = card or kwargs
        if card:
            self.fillFrom(card)

    def _tag_n(self, tag: str, data: dict[str, str] | None) -> None:
        """Set the structured name (N) field.

        Args:
            tag: The tag name (always 'n').
            data: Dictionary with keys: family, given, additional, prefix, suffix.
        """
        if data:
            self.j.add("n")
            if data.get("family"):
                self.j.n.value.family = data["family"]
            if data.get("given"):
                self.j.n.value.given = data["given"]
            if data.get("additional"):
                self.j.n.value.additional = data["additional"]
            if data.get("prefix"):
                self.j.n.value.prefix = data["prefix"]
            if data.get("suffix"):
                self.j.n.value.suffix = data["suffix"]

    def _tag_adr(self, tag: str, data: dict[str, str] | None) -> None:
        """Set the structured address (ADR) field.

        Args:
            tag: The tag name (always 'adr').
            data: Dictionary with keys: box, city, code, country, extended,
                lines, region, street.
        """
        if data:
            # 'box', 'city', 'code', 'country', 'extended', 'lines', 'one_line', 'region', 'street'
            self.j.add("adr")
            if data.get("box"):
                self.j.adr.value.box = data["box"]
            if data.get("city"):
                self.j.adr.value.city = data["city"]
            if data.get("code"):
                self.j.adr.value.code = data["code"]
            if data.get("country"):
                self.j.adr.value.country = data["country"]
            if data.get("extended"):
                self.j.adr.value.extended = data["extended"]
            if data.get("lines"):
                self.j.adr.value.lines = data["lines"]
            if data.get("region"):
                self.j.adr.value.region = data["region"]
            if data.get("street"):
                self.j.adr.value.street = data["street"]

    def doserialize(self) -> str:
        """Serialize the vCard to string format.

        Returns:
            The vCard as a serialized string.
        """
        return self.j.serialize()

    def doprettyprint(self) -> str:
        """Get a pretty-printed representation of the vCard.

        Returns:
            Pretty-printed vCard string.
        """
        return self.j.prettyPrint()

    def setTag(self, tag: str, data: dict[str, Any] | None) -> None:
        """Set a vCard tag with the given data.

        Args:
            tag: The vCard tag name (lowercase).
            data: Dictionary containing the tag data. For simple tags, uses
                '#0', '#1', etc. keys for values and '%s?param_list' for params.

        Raises:
            AssertionError: If the tag is not a valid vCard tag.
        """
        if data:
            logger.debug("%s %s", tag, data)
            assert tag in VALID_VCARD_TAGS, "ERROR: %s is not a valid tag" % tag
            if tag in ["n", "adr"]:
                getattr(self, "%s%s" % ("_tag_", tag))(tag, data)
            else:
                count = 0
                for k2, v2 in list(data.items()):
                    if v2:
                        path = "#%i" % count
                        count = count + 1
                        m = self.j.add(tag)
                        setattr(m, "value", data[path])
                        if tag == "org":
                            m.isNative = False
                        attrlist = data.get("%s?param_list" % path)
                        if attrlist:
                            setattr(m, "type_paramlist", attrlist)

    def fillFrom(self, card: dict[str, Any]) -> None:
        """Fill the vCard from a dictionary of tag data.

        Args:
            card: Dictionary mapping tag names to their data.
        """
        logger.debug("card_bag %s", card)

        for tag, v in list(card.items()):
            # REVIEW:SMELL — all branches do the same thing
            if tag == "n":
                self.setTag(tag, v)
            elif tag == "adr":
                self.setTag(tag, v)
            else:
                self.setTag(tag, v)


__all__ = ["VCard", "VALID_VCARD_TAGS"]
