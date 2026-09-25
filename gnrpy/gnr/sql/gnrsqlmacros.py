#-*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqlmacros : backend independent SQL macros
# Copyright (c) : 2004 - 2026 Softwell sas - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""The SQL macros that do not depend on the database engine.

A macro is four things, and ``db.addMacro(name, regex, callback,
contexts=...)`` registers them together:

    name
        The macro name without ``#`` (e.g. ``'IN_RANGE'``).
    regex
        The compiled regex matching the macro call in the SQL text.
    callback
        ``callback(match, compiler) -> str``, the replacement.  *match* is
        the regex match, *compiler* the :class:`SqlQueryCompiler` running
        the compilation: the callback reads ``compiler.sqlparams``,
        ``compiler.db`` and ``compiler.cpl`` from it.
    contexts
        Comma separated names of the compilation points where the macro is
        expanded, or ``None`` for every one of them.

The seven context names are ``formula_pre`` and ``formula_post`` (a
``sql_formula``, before and after the ``$column`` translation),
``join_cnd`` (the ``cnd`` of a join), ``where``, ``columns``,
``columns_final`` (the select list, last step) and ``order_by``; the
tuple ``MACRO_CONTEXTS`` lists them.

``SQL_MACROS`` is registered by ``GnrSqlDb.registerMacros``, ``APP_MACROS``
by ``GnrSqlAppDb.registerMacros``: the tuples are in registration order,
which is the order of expansion inside a context.  Engine specific macros
live in the adapter module that registers them (e.g. ``POSTGRES_MACROS`` in
``gnr/sql/adapters/_gnrbasepostgresadapter.py``).
"""

import re

from gnr.core.gnrdate import decodeDatePeriod

# The compilation points where SqlQueryCompiler calls
# macro_expander.replace_context(); db.addMacro() accepts no other name.
MACRO_CONTEXTS = ('formula_pre', 'formula_post', 'join_cnd', 'where',
                  'columns', 'columns_final', 'order_by')

IN_RANGEFINDER = re.compile(r"#IN_RANGE\s*\(\s*((?:\$|@|\:)?[\w\.\@]+)\s*,\s*((?:\$|@|\:)?[\w\.\@]+)\s*,\s*((?:\$|@|\:)?[\w\.\@]+)\s*\)\s*",re.MULTILINE)
PERIODFINDER = re.compile(r"#PERIOD\s*\(\s*((?:\$|@)?[\w\.\@]+)\s*,\s*:?(\w+)\)")

BAGEXPFINDER = re.compile(r"#BAG\s*\(\s*((?:\$|@)?[\w\.\@]+)\s*\)(\s*AS\s*(\w*))?")
BAGCOLSEXPFINDER = re.compile(r"#BAGCOLS\s*\(\s*((?:\$|@)?[\w\.\@]+)\s*\)(\s*AS\s*(\w*))?")


def expand_bag(match, compiler):
    """Regex callback: expand a ``#BAG($field) AS alias`` macro.

    Registers the column for post-query Bag evaluation (the raw value
    will be parsed into a ``Bag`` object after fetching).

    Args:
        match: Regex match object with groups (1) field, (3) optional alias.
        compiler: The ``SqlQueryCompiler`` running the compilation.

    Returns:
        str: The column expression, optionally with ``AS alias``.
    """
    fld = match.group(1)
    asfld = match.group(3)
    compiler.cpl.evaluateBagColumns.append(((asfld or fld).replace('$',''),False))
    return fld if not asfld else '{} AS {}'.format(fld, asfld)


def expand_bagcols(match, compiler):
    """Regex callback: expand a ``#BAGCOLS($field) AS alias`` macro.

    Like ``expand_bag`` but the second element of the registered tuple
    is ``True``, signalling that the Bag should be expanded into
    individual columns.

    Args:
        match: Regex match object with groups (1) field, (3) optional alias.
        compiler: The ``SqlQueryCompiler`` running the compilation.

    Returns:
        str: The column expression, optionally with ``AS alias``.
    """
    fld = match.group(1)
    asfld = match.group(3)
    compiler.cpl.evaluateBagColumns.append(((asfld or fld).replace('$',''),True))
    return fld if not asfld else '{} AS {}'.format(fld, asfld)


def expand_in_range(match, compiler):
    """Regex callback: expand ``#IN_RANGE(value, low, high)`` into SQL.

    Generates a four-branch OR expression that handles NULLs on either
    bound:

    - Only high bound present: ``value <= high``.
    - Only low bound present: ``value >= low``.
    - Both bounds present: ``low <= value <= high``.
    - Both NULL: always true.

    Args:
        match: Regex match object with groups (1) value_field,
            (2) low_field, (3) high_field.
        compiler: The ``SqlQueryCompiler`` running the compilation.

    Returns:
        str: SQL fragment implementing the inclusive range check.
    """
    # Example: #IN_RANGE($dataLavoro,$dataInizioValidita,$dataFineValidita)
    value_field = match.group(1)
    low_field = match.group(2)
    high_field = match.group(3)

    result = f"""
                (({low_field} IS NULL AND {high_field} IS NOT NULL AND {value_field}<={high_field}) OR
                ({low_field} IS NOT NULL AND {high_field} IS NULL AND {value_field}>={low_field}) OR
                ({low_field} IS NOT NULL AND {high_field} IS NOT NULL AND
                    {value_field} >= {low_field} AND {value_field} <= {high_field}) OR
                ({low_field} IS NULL AND {high_field} IS NULL))
            """
    return result


def expand_period(match, compiler):
    """Regex callback: expand ``#PERIOD($field, param)`` into a date range.

    Decodes the period string stored in ``compiler.sqlparams[param]``
    (e.g. ``'2024Q1'``, ``'202401'``) into concrete ``date_from`` /
    ``date_to`` values via ``decodeDatePeriod``, then generates the
    appropriate SQL predicate:

    - Both dates present and equal: ``field = :param_from``.
    - Both dates present: ``field BETWEEN :param_from AND :param_to``.
    - Only from: ``field >= :param_from``.
    - Only to: ``field <= :param_to``.
    - Neither: ``true`` (no filtering).

    Side effect: adds ``param_from`` and/or ``param_to`` keys to
    ``compiler.sqlparams``.

    Args:
        match: Regex match object with groups (1) field, (2) param name.
        compiler: The ``SqlQueryCompiler`` running the compilation.

    Returns:
        str: SQL fragment for the period filter.
    """
    fld = match.group(1)
    period_param = match.group(2)
    date_from, date_to = decodeDatePeriod(compiler.sqlparams[period_param],
                                          workdate=compiler.db.workdate,
                                          returnDate=True, locale=compiler.db.locale)
    from_param = '%s_from' % period_param
    to_param = '%s_to' % period_param

    # Branch: no date boundaries -- no filtering
    if date_from is None and date_to is None:
        return ' true'
    # Branch: both boundaries present
    elif date_from and date_to:
        if date_from == date_to:
            # Single-day period
            compiler.sqlparams[from_param] = date_from
            return ' %s = :%s ' % (fld, from_param)

        compiler.sqlparams[from_param] = date_from
        compiler.sqlparams[to_param] = date_to
        # REVIEW: TODO -- replace the native SQL BETWEEN with >= / < for
        # consistency with date handling (SQL BETWEEN is inclusive on
        # both bounds).
        result = ' (%s BETWEEN :%s AND :%s) ' % (fld, from_param, to_param)
        return result

    # Branch: only lower bound
    elif date_from:
        compiler.sqlparams[from_param] = date_from
        return ' %s >= :%s ' % (fld, from_param)
    # Branch: only upper bound
    else:
        compiler.sqlparams[to_param] = date_to
        return ' %s <= :%s ' % (fld, to_param)


# name -> (regex, callback, contexts), in registration order
SQL_MACROS = (('IN_RANGE', IN_RANGEFINDER, expand_in_range, 'where,formula_post,join_cnd'),
              ('PERIOD', PERIODFINDER, expand_period, 'where'))

APP_MACROS = (('BAG', BAGEXPFINDER, expand_bag, 'columns'),
              ('BAGCOLS', BAGCOLSEXPFINDER, expand_bagcols, 'columns'))
