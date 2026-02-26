# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy core - see LICENSE for details
# module gnrnumber : Decimal number utilities
# Copyright (c) : 2004 - 2015 Softwell sas - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari
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
"""gnrnumber - Decimal number utilities.

This module provides utilities for working with Decimal numbers, including
rounding, conversion from floats, and percentage calculations.

Functions:
    decimalRound: Round a value to a specified number of decimal places.
    floatToDecimal: Convert a float to a Decimal with optional rounding.
    calculateMultiPerc: Calculate cumulative percentage from a string.
    partitionTotals: Partition totals according to given quotes.
"""

from __future__ import annotations

from collections.abc import Generator, Iterable
from decimal import ROUND_HALF_UP, Decimal


def decimalRound(
    value: float | Decimal | None = None,
    places: int = 2,
    rounding: str | None = None,
) -> Decimal:
    """Round a value to a specified number of decimal places.

    Args:
        value: The value to round. If None, defaults to 0.
        places: Number of decimal places to round to. Defaults to 2.
        rounding: Rounding mode from decimal module. Defaults to ROUND_HALF_UP.

    Returns:
        The rounded Decimal value.

    Example:
        >>> decimalRound(17.382)
        Decimal('17.38')
        >>> decimalRound(17.382, places=1)
        Decimal('17.4')
    """
    value = value or 0
    if not isinstance(value, Decimal):
        value = floatToDecimal(value)
    return value.quantize(  # type: ignore[union-attr]
        Decimal(str(10**-places)),
        rounding=rounding or ROUND_HALF_UP,
    )


def floatToDecimal(
    f: float | None,
    places: int | None = None,
    rounding: str | None = None,
) -> Decimal | None:
    """Convert a float to a Decimal with optional rounding.

    Args:
        f: The float value to convert. If None, returns None.
        places: Optional number of decimal places to round to.
        rounding: Optional rounding mode from decimal module.

    Returns:
        The Decimal representation of the float, or None if input is None.

    Example:
        >>> floatToDecimal(17.352)
        Decimal('17.352')
        >>> floatToDecimal(17.352, places=2)
        Decimal('17.35')
    """
    if f is None:
        return None
    result = Decimal(str(f))
    if places:
        return decimalRound(result, places=places, rounding=rounding)
    return result


def calculateMultiPerc(multiperc: str | None) -> Decimal | None:
    """Calculate cumulative percentage from a string of percentages.

    Takes a string of percentages separated by '+' and calculates the
    cumulative effect of applying them sequentially.

    Args:
        multiperc: A string of percentages separated by '+', e.g., "10+5+3".

    Returns:
        The cumulative percentage as a Decimal, or None if input is empty.

    Example:
        >>> calculateMultiPerc("10+5")
        Decimal('14.50')
    """
    if not multiperc:
        return None
    multiperc_list = multiperc.split("+")
    t = Decimal(100)
    while multiperc_list:
        s = Decimal(multiperc_list.pop(0))
        t -= t * s / 100
    return decimalRound(100 - t)


def partitionTotals(
    totals: Decimal | str | Iterable[Decimal | str],
    quotes: Iterable[Decimal | str],
    places: int = 2,
    rounding: str | None = None,
) -> Generator[list[Decimal] | Generator[Decimal, None, None], None, None]:
    """Partition totals according to given quotes.

    Distributes one or more totals across partitions according to the
    proportions specified in quotes. The last partition receives the
    residue to ensure the sum equals the original totals.

    Args:
        totals: A single value or list of values to partition.
        quotes: The proportions for each partition.
        places: Number of decimal places for rounding. Defaults to 2.
        rounding: Rounding mode from decimal module.

    Yields:
        For each quote, a list of partitioned amounts (one per total).
        The last yield is a generator of residues.

    Example:
        >>> list(partitionTotals([100], [10, 70, 20]))
        [[Decimal('10.00')], [Decimal('70.00')], <generator object...>]
    """
    if not isinstance(totals, list):
        totals = [totals]  # type: ignore[list-item]
    totals_dec = list(map(Decimal, totals))  # type: ignore[arg-type]
    quotes_dec = list(map(Decimal, quotes))  # type: ignore[arg-type]
    residues = list(totals_dec)
    tot_quotes = sum(quotes_dec)
    n_quotes = len(quotes_dec)
    for idx, q in enumerate(quotes_dec):
        if idx + 1 == n_quotes:
            yield (decimalRound(r, places=places, rounding=rounding) for r in residues)
            return
        result: list[Decimal] = []
        for j, tot in enumerate(totals_dec):
            tot_rounded = decimalRound(tot * q / tot_quotes)
            result.append(tot_rounded)
            residues[j] = residues[j] - tot_rounded
        yield result


__all__ = [
    "decimalRound",
    "floatToDecimal",
    "calculateMultiPerc",
    "partitionTotals",
]
