# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqlmodel.helpers : Standalone helper functions and exceptions
# Copyright (c) : 2004 - 2026 Softwell srl - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari, Francesco Cavazzana
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

"""Standalone helper functions and exception classes for the model layer.

Contains formula-building helpers (``bagItemFormula``, ``toolFormula``)
and exception types used across the model package.
"""

from __future__ import annotations

from typing import Any


def bagItemFormula(
    bagcolumn: str | None = None,
    itempath: str | None = None,
    dtype: str | None = None,
    kwargs: dict[str, Any] | None = None,
) -> str:
    """Build a SQL formula to extract a value from a Bag XML column.

    Constructs a ``CAST(xpath(...))`` expression that extracts a specific
    item from a Bag column stored as XML, optionally casting it to the
    requested data type.

    Args:
        bagcolumn: The SQL column name containing the Bag XML data.
        itempath: Dot-separated path to the item inside the Bag.
            Segments starting with ``#`` are treated as positional
            indexes (zero-based).  A trailing ``?attr`` syntax extracts
            an XML attribute instead of the text content.
        dtype: Target GenroPy data type code (``'T'``, ``'N'``,
            ``'D'``, etc.).  Defaults to ``'T'`` (text).
        kwargs: Mutable dict that receives the ``var_calculated_path``
            SQL parameter binding.

    Returns:
        A SQL expression string ready for use in a ``formulaColumn``.
    """
    itemlist = itempath.split('.')
    last_chunk = itemlist[-1]
    suffix = 'text()'
    if '?' in last_chunk:
        last_chunk, searchattr = last_chunk.split('?')
        suffix = f'@{searchattr}'
        itemlist[-1] = last_chunk
    itempath = '/'.join([
        c if not c.startswith('#') else f'*[{int(c[1:]) + 1}]'
        for c in itemlist
    ])
    sql_formula = (
        f" CAST( (xpath(:calculated_path, CAST({bagcolumn} as XML) ) )[1]  AS text)"
    )
    kwargs['var_calculated_path'] = f'/GenRoBag/{itempath}/{suffix}'
    dtype = dtype or 'T'
    # REVIEW: hardcoded PostgreSQL type map — will break on other
    # backends.  Consider using adapter-level type mapping.
    typeconverter = {
        'T': 'text', 'A': 'text', 'C': 'text', 'P': 'text',
        'N': 'numeric', 'B': 'boolean', 'D': 'date',
        'H': 'time without time zone', 'L': 'bigint', 'R': 'real',
        'X': 'text',
    }
    desttype = typeconverter[dtype]
    if desttype != 'text':
        return "CAST ( ( %s ) AS %s) " % (sql_formula, desttype)
    return sql_formula


def toolFormula(
    tool: str,
    dtype: str | None = None,
    kwargs: dict[str, Any] | None = None,
) -> str:
    """Build a SQL formula for a tool-link column.

    Generates an HTML anchor (or image tag) pointing to the tool URL
    for the current record.

    Args:
        tool: The tool identifier used in the URL path.
        dtype: If ``'P'``, generates an ``<img>`` tag; otherwise an
            ``<a>`` tag.
        kwargs: Column attribute dict — may contain ``format_class``,
            ``iconClass``, ``link_text``, and ``name_long``.

    Returns:
        A SQL expression string producing an HTML snippet.
    """
    result = f"(:env_external_host || '/_tools/{tool}?record_pointer=' || $__record_pointer)"
    _class = kwargs.get('format_class', '')
    if _class:
        _class = f'class="{_class}"'
    if dtype == 'P':
        result = f"""format('<img {_class} src="%%s"/>', {result})"""
    else:
        iconClass = kwargs.get('iconClass')
        if iconClass:
            contentHTML = f""" '<div class="{iconClass}">&nbsp;</div>' """
        else:
            contentHTML = kwargs.get('link_text') or kwargs.get('name_long')
        result = f"""format('<a {_class} href="%%s">%%s</a>', {result},{contentHTML})"""
    return result


class NotExistingTableError(Exception):
    """Raised when a referenced table does not exist in the model."""
    pass


class ConfigureAfterStartError(Exception):
    """Raised when model configuration is attempted after ``startup()``."""
    pass
