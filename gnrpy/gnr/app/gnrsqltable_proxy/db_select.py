# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy app - see LICENSE for details
# module gnrsqltable_proxy.db_select : table level part of the dbSelect flows
# Copyright (c)     : 2004 - 2026 Softwell sas - Milano
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

"""Table level part of the ``db_select`` mixin.

:class:`DbSelectProxy` is attached to every table of a ``GnrApp`` database by
``gnr.app.gnrdbo.TableBase.dbSelectProxy``.  It is the third sibling of
:class:`gnr.app.gnrsqltable_proxy.selection.SelectionProxy`, which serves the
grid selection, and of
:class:`gnr.app.gnrsqltable_proxy.record.RecordProxy`, which serves the
record flows.

It carries two groups of methods.  The first is the search of the ``dbSelect``
widget: the column sets, the fetch by identifier and the four stage search.
The second is the three other table services the same mixin exposes —
``tableAnalyzeStore``, ``getValuesString`` and ``getMultiFetch`` — each a few
lines of pure table work with no page dependency.

It never references a web page.  What the page provides — the locale, the
localizer, the resolved select handler and applymethod — is applied by the
caller or passed in as a callable.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Optional

from gnr.core import gnrlist

ESCAPE_SPECIAL = re.compile(r'[\[\\\^\$\.\|\?\*\+\(\)\]\{\}]')
"""The characters removed from the user input before it becomes a regex."""

PREFERRED_COLUMN = ("(CASE WHEN %s IS NOT TRUE THEN 'not_preferred_row'"
                    " ELSE '' END) AS _customclasses_preferred")
"""The CSS class column the widget reads to grey the non preferred rows."""

INVALID_ITEM_COLUMN = '(%s IS TRUE) AS _is_invalid_item'
"""The boolean column the widget reads to mark an invalid row."""


class DbSelectProxy:
    """dbSelect proxy of a single table."""

    def __init__(self, tblobj: Any) -> None:
        self.tblobj = tblobj

    @property
    def db(self) -> Any:
        """The database of the proxied table."""
        return self.tblobj.db

    # ------------------------------------------------------------------
    #  Columns
    # ------------------------------------------------------------------

    def composeQueryColumns(self, columns: Optional[str] = None,
                            rowcaption: Optional[str] = None) -> list:
        """Return the columns the search matches the typed text on.

        Args:
            columns: The columns to search on.  When absent the table
                queryfields are used, and failing those the caption columns.
            rowcaption: A caption template overriding the table one.

        Returns:
            The query columns.
        """
        tblobj = self.tblobj
        return tblobj.getQueryFields(columns,
                                     tblobj.rowcaptionDecode(rowcaption)[0])

    def composeShowColumns(self, rowcaption: Optional[str] = None,
                           auxColumns: Optional[str] = None) -> list:
        """Return the columns the dropdown displays.

        Args:
            rowcaption: A caption template overriding the table one.
            auxColumns: Extra columns to display.

        Returns:
            The caption columns followed by the auxiliary ones.
        """
        tblobj = self.tblobj
        return gnrlist.merge(tblobj.rowcaptionDecode(rowcaption)[0],
                             tblobj.columnsFromString(auxColumns))

    def composeResultColumns(self, rowcaption: Optional[str] = None,
                             auxColumns: Optional[str] = None,
                             hiddenColumns: Optional[str] = None,
                             alternatePkey: Optional[str] = None) -> list:
        """Return the columns the query fetches.

        Args:
            rowcaption: A caption template overriding the table one.
            auxColumns: Extra columns to display.
            hiddenColumns: Extra columns to fetch without displaying them.
            alternatePkey: A column used in place of the pkey; it joins the
                result columns with a ``$`` prefix unless it has one.

        Returns:
            The displayed columns, the caption ones, the hidden ones and the
            alternate pkey.
        """
        tblobj = self.tblobj
        result = gnrlist.merge(self.composeShowColumns(rowcaption=rowcaption,
                                                       auxColumns=auxColumns),
                               tblobj.rowcaptionDecode(rowcaption)[0],
                               tblobj.columnsFromString(hiddenColumns))
        if alternatePkey and alternatePkey not in result:
            result.append(alternatePkey if alternatePkey.startswith('$')
                          else '$%s' % alternatePkey)
        return result

    def addSearchFlagColumns(self, resultcolumns: list,
                             preferred: Optional[str] = None,
                             invalidItemCondition: Optional[str] = None) -> list:
        """Return the result columns with the two flag columns the widget reads.

        Both take a raw SQL expression from the caller and land under a fixed
        alias: ``_customclasses_preferred`` carries the CSS class of a row that
        is *not* preferred, ``_is_invalid_item`` a boolean.

        Args:
            resultcolumns: The columns of :meth:`composeResultColumns`.
            preferred: A SQL expression true for the preferred rows.
            invalidItemCondition: A SQL expression true for the invalid ones.

        Returns:
            A new list; *resultcolumns* is not modified.
        """
        result = list(resultcolumns)
        if preferred:
            result.append(PREFERRED_COLUMN % preferred)
        if invalidItemCondition:
            result.append(INVALID_ITEM_COLUMN % invalidItemCondition)
        return result

    def composeColumnHeaders(self, selection: Any, showcolumns: list,
                             translate: Callable[[str], str]) -> tuple[str, str]:
        """Return the displayed column aliases and their localized headers, both comma separated.

        A column header is its ``name_short`` when it has one, its ``label``
        otherwise, and it goes through *translate* — the page localizer, passed
        in because the proxy has no page.

        Args:
            selection: The selection the search produced.
            showcolumns: The columns of :meth:`composeShowColumns`.
            translate: The localizer, a one argument callable.

        Returns:
            A tuple of two comma separated strings, ``(columns, headers)``.
        """
        showcols = [self.tblobj.colToAs(c.lstrip('$')) for c in showcolumns]
        colAttrs = selection.colAttrs
        headers = [translate(colAttrs[k].get('name_short') or colAttrs[k]['label'])
                   for k in showcols]
        return ','.join(showcols), ','.join(headers)

    # ------------------------------------------------------------------
    #  Table defaults of the search
    # ------------------------------------------------------------------

    def resolvePreferredExpression(self, preferred: Optional[str] = None) -> Optional[str]:
        """Return the SQL expression that marks the preferred rows.

        An explicit falsy value from the caller wins: only ``None`` falls back.
        """
        return self.tblobj.attributes.get('preferred') if preferred is None else preferred

    def resolveWeakCondition(self, weakCondition: Any = False) -> Any:
        """Return the weak condition, the table attribute when the caller sends none.

        The caller has already switched *weakCondition* off when a selectmethod
        is in play; the table attribute is read here, after that, so a table
        that declares ``weakCondition`` re-enables it.  That ordering is the
        behaviour of the frozen handler and is kept on purpose.
        """
        return weakCondition or self.tblobj.attributes.get('weakCondition')

    def composeSearchOrderBy(self, order_by: Optional[str], showcolumns: list,
                             preferred: Optional[str] = None) -> str:
        """Return the ORDER BY of the search, the preferred term first.

        The preferred rows come first when a preferred expression is given.
        The column ordering is the caller's *order_by*, failing that the table
        ``order_by`` attribute, failing that the first displayed column; it is
        prefixed with ``$`` unless it already starts with ``$`` or ``@``.

        Args:
            order_by: The caller's ordering, or ``None``.
            showcolumns: The columns of :meth:`composeShowColumns`.
            preferred: The expression of :meth:`resolvePreferredExpression`.

        Returns:
            The comma separated ORDER BY.
        """
        order_list = []
        if preferred:
            order_list.append('( %s ) desc' % preferred)
        order_by = order_by or self.tblobj.attributes.get('order_by') or showcolumns[0]
        order_list.append(order_by if order_by[0] in ('$', '@') else '$%s' % order_by)
        return ', '.join(order_list)

    # ------------------------------------------------------------------
    #  Fetch by identifier
    # ------------------------------------------------------------------

    def selectRecordById(self, _id: str, resultcolumns: list,
                         condition: Optional[str] = None,
                         weakCondition: Any = False,
                         alternatePkey: Optional[str] = None,
                         excludeDraft: bool = True,
                         **kwargs: Any) -> tuple[Any, list]:
        """Return the single row the widget shows and the errors the fetch collected.

        The row wins over the condition: when a condition is given and the
        first fetch finds nothing, the same row is fetched again without it and
        the caller is told through the returned errors.  A logically deleted
        row is returned on purpose, so that a field pointing at one still
        displays its caption.

        Args:
            _id: The value of the identifier column.
            resultcolumns: The columns of :meth:`composeResultColumns`.
            condition: An extra SQL condition.
            weakCondition: ``True`` makes this fetch ignore *condition*
                altogether.
            alternatePkey: The identifier column, ``pkey`` when absent.
            excludeDraft: Leave the draft rows out.
            **kwargs: Forwarded to the query.

        Returns:
            A tuple ``(selection, errors)``, *errors* being a list of strings.
        """
        where = '$%s = :id' % (alternatePkey or 'pkey')
        fullwhere = ('( %s ) AND ( %s ) ' % (where, condition)
                     if (condition and weakCondition is not True) else where)
        selection = self._fetchById(fullwhere, _id, resultcolumns,
                                    excludeDraft, kwargs)
        if condition and not selection:
            selection = self._fetchById(where, _id, resultcolumns,
                                        excludeDraft, kwargs)
            return selection, ['current value does not fit condition']
        return selection, []

    def _fetchById(self, where: str, _id: str, resultcolumns: list,
                   excludeDraft: bool, kwargs: dict) -> Any:
        """One row by identifier, logically deleted rows included."""
        return self.tblobj.query(columns=','.join(resultcolumns), where=where,
                                 excludeLogicalDeleted=False,
                                 excludeDraft=excludeDraft,
                                 limit=1, id=_id, **kwargs).selection()

    # ------------------------------------------------------------------
    #  The four stage search
    # ------------------------------------------------------------------

    def searchRecords(self, querycolumns: list, querystring: str,
                      resultcolumns: list, condition: Optional[str] = None,
                      exclude: Optional[Any] = None,
                      limit: Optional[int] = None,
                      order_by: Optional[str] = None,
                      **kwargs: Any) -> Any:
        """Return the selection of the matching records, widening the match until something is found.

        Four stages, each one run only if the previous left the result unusable:

        1. ``contains`` on the first query column;
        2. ``startswith`` on it, when stage 1 filled the page — a full page
           means the user has not typed enough to be specific;
        3. a case insensitive regex per word, on the word boundary, over the
           concatenation of every query column, when nothing was found;
        4. ``ILIKE`` per word over the same concatenation, when still nothing.

        Stages 3 and 4 differ in more than the operator: the regex one splits
        the query string as the user typed it, after the special characters are
        removed, the ILIKE one splits it on whitespace.

        Args:
            querycolumns: The columns of :meth:`composeQueryColumns`.
            querystring: What the user typed.
            resultcolumns: The columns to fetch.
            condition: An extra SQL condition, AND-ed with every stage.
            exclude: Primary keys to leave out, as a comma separated string or
                as an iterable.
            limit: The page size; it is also the threshold of stage 2.
            order_by: The ordering of :meth:`composeSearchOrderBy`.
            **kwargs: Forwarded to the query.  A ``where`` among them is
                discarded: the stage owns the WHERE.

        Returns:
            The selection of the first stage that produced one.
        """
        exclude_list = self.parseExcludeList(exclude)
        condition = self.composeExcludeCondition(condition, exclude_list)
        kwargs.pop('where', None)

        def stageSelection(where: Optional[str], **searchargs: Any) -> Any:
            """One stage: compose the WHERE and run the query."""
            queryargs = dict(kwargs)
            queryargs.update(searchargs)
            if where and condition:
                where = '( %s ) AND ( %s ) ' % (where, condition)
            else:
                where = where or condition
            return self.tblobj.query(where=where,
                                     columns=','.join(resultcolumns),
                                     limit=limit,
                                     order_by=order_by or querycolumns[0],
                                     exclude_list=exclude_list,
                                     **queryargs).selection(_aggregateRows=True)

        def operatorStage(op: str, searchval: str) -> Any:
            """Stage 1 and stage 2: one operator on the first query column."""
            sqlArgs: dict = {}
            cond = self.tblobj.opTranslate(querycolumns[0], op, searchval,
                                           sqlArgs=sqlArgs)
            return stageSelection(cond, **sqlArgs)

        srclist = querystring.split()
        if not srclist:
            return stageSelection(None)
        searchval = '%s%%' % ('%% '.join(srclist))
        result = operatorStage('contains', searchval)
        if len(result) >= (limit or 50):
            result = operatorStage('startswith', searchval)
        if len(result) == 0:
            words = [w for w in re.split(' ', ESCAPE_SPECIAL.sub('', querystring)) if w]
            if words:
                where, whereargs = self._wordsStage(querycolumns, words, '~*',
                                                    '(^|\\W)%s')
                result = stageSelection(where, **whereargs)
        if len(result) == 0:
            where, whereargs = self._wordsStage(querycolumns, srclist, 'ILIKE',
                                                '%%%s%%')
            result = stageSelection(where, **whereargs)
        return result

    def _wordsStage(self, querycolumns: list, words: list, operator: str,
                    mask: str) -> tuple[str, dict]:
        """One condition per word over the concatenation of the query columns.

        Returns:
            A tuple ``(where, whereargs)``, ready for the stage query.
        """
        columns_concat = " || ' ' || ".join(
            ["CAST ( COALESCE(%s,'') AS TEXT ) " % c for c in querycolumns])
        whereargs = dict([('w%i' % i, mask % w.strip())
                          for i, w in enumerate(words)])
        where = " AND ".join(["(%s)  %s :w%i" % (columns_concat, operator, i)
                              for i, w in enumerate(words)])
        return where, whereargs

    def parseExcludeList(self, exclude: Optional[Any] = None) -> Optional[list]:
        """Return the primary keys to leave out, as a list.

        A string is split on commas; an iterable keeps only its truthy entries,
        because a ``None`` among them breaks the query.

        Returns:
            The list, or ``None`` when nothing is excluded.
        """
        if not exclude:
            return None
        if isinstance(exclude, str):
            return [t.strip() for t in exclude.split(',')]
        return [t for t in exclude if t]

    def composeExcludeCondition(self, condition: Optional[str],
                                exclude_list: Optional[list]) -> Optional[str]:
        """Return *condition* with the exclusion ANDed in, so that every stage carries it."""
        if not exclude_list:
            return condition
        exclude_cond = 'NOT ($pkey IN :exclude_list )'
        if condition:
            return '%s AND %s' % (condition, exclude_cond)
        return exclude_cond

    # ------------------------------------------------------------------
    #  The other services of the mixin
    # ------------------------------------------------------------------

    def selectRecordsToTotalize(self, where: Optional[str] = None,
                                group_by: Optional[list] = None,
                                **kwargs: Any) -> Any:
        """Return the selection ``tableAnalyzeStore`` totalizes.

        *group_by* is consumed twice with two meanings, here as the column list
        and in ``totalize`` as the grouping specification, so the callables it
        may contain are columns for nobody and are dropped here.

        Args:
            where: The SQL WHERE clause.
            group_by: The grouping specification.
            **kwargs: Forwarded to the query.

        Returns:
            The selection.
        """
        columns = [x for x in group_by if not callable(x)]
        return self.tblobj.query(where=where, columns=','.join(columns),
                                 **kwargs).selection()

    def composeValuesString(self, caption_field: Optional[str] = None,
                            alt_pkey_field: Optional[str] = None,
                            **kwargs: Any) -> str:
        """Return the rows as a ``key:caption`` comma separated string.

        The format is lossy on purpose: a comma inside a caption becomes a
        space, because the comma is the separator, and a missing caption
        becomes the empty string.

        Args:
            caption_field: The caption column; the table ``caption_field``
                attribute when absent, and the pkey when there is none.
            alt_pkey_field: The key column; the pkey when absent.
            **kwargs: Forwarded to the query.

        Returns:
            A string like ``"key1:caption1,key2:caption2"``.
        """
        tblobj = self.tblobj
        pkey = alt_pkey_field or tblobj.pkey
        caption_field = caption_field or tblobj.attributes.get('caption_field') or tblobj.pkey
        rows = tblobj.query(columns='$%s,$%s' % (pkey, caption_field),
                            **kwargs).fetch()
        return ','.join(['%s:%s' % (r[pkey], (r[caption_field] or '').replace(',', ' '))
                         for r in rows])

    def fetchRecordsAsBag(self, columns: Optional[str] = None, **kwargs: Any) -> Any:
        """Return one query of ``getMultiFetch`` as a :class:`Bag` keyed by pkey.

        Args:
            columns: The columns to fetch; ``'*'`` and ``None`` both mean all
                of them and reach the query unchanged, because
                ``columnsFromString`` would turn ``'*'`` into ``'$*'``.
            **kwargs: Forwarded to the query.

        Returns:
            A :class:`gnr.core.gnrbag.Bag`, one node per row.
        """
        if columns and columns != '*':
            columns = ','.join(self.tblobj.columnsFromString(columns))
        else:
            columns = '*'
        return self.tblobj.query(columns=columns, **kwargs).fetchAsBag('pkey')
