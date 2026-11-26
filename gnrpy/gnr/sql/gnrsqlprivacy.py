# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqlprivacy : census of the columns holding personal data
# Copyright (c) : 2004 - 2026 Softwell srl - Milano
# --------------------------------------------------------------------------
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

"""Census of the columns holding personal data.

A column is marked as personal data by ``variant='masked'`` with
``variant_masked_mode=<kind>``, or by the ``encrypted`` attribute (see
:attr:`~gnr.sql.gnrsqltable.columns.ColumnsMixin.privacy_columns`).
The report reads the model only, never the data in the tables.

The TSV form is a contract read by other tools: its header and its
``status`` values must not change.
"""

TSV_HEADER = ('package', 'table', 'column', 'status', 'kind')

# Matched anywhere in the column name
SUSPECT_SUBSTRINGS = (
    'codice_fiscale', 'partita_iva', 'email', 'telefono', 'cellulare',
    'indirizzo', 'iban', 'cognome', 'nominativo', 'ragione_sociale',
    'nascita', 'firstname', 'lastname', 'surname', 'phone', 'mobile',
    'address', 'street', 'birth', 'fiscal',
)

# Matched only as a whole '_'-separated token of the column name
SUSPECT_TOKENS = frozenset((
    'cf', 'piva', 'vat', 'pec', 'tel', 'cell', 'fax', 'via', 'nome', 'name',
    'note', 'notes',
))


def is_suspect_column(colname):  # wf:phase-1:new
    """Return ``True`` when the column name suggests personal data."""
    colname = colname.lower()
    if any(pattern in colname for pattern in SUSPECT_SUBSTRINGS):
        return True
    return not SUSPECT_TOKENS.isdisjoint(colname.split('_'))


def privacy_report(db):  # wf:phase-1:new
    """Classify the physical columns of every table of ``db``.

    :returns: a list of ``(package, table, column, status, kind)`` tuples,
        where ``package`` is the package declaring the column, ``table`` is
        ``pkg.table``, ``status`` is ``marked`` (marked with a kind),
        ``nokind`` (marked without a kind) or ``suspect`` (not marked, but
        its name suggests personal data), and ``kind`` is ``''`` when none.
        Columns that are neither marked nor suspect are left out.
    """
    rows = []
    for pkg in db.packages.values():
        for tblobj in pkg.tables.values():
            marked = tblobj.dbtable.privacy_columns
            for colname, colobj in tblobj.columns.items():
                if colname in marked:
                    kind = marked[colname] or ''
                    status = 'marked' if kind else 'nokind'
                elif is_suspect_column(colname):
                    kind = ''
                    status = 'suspect'
                else:
                    continue
                owner = colobj.attributes.get('_owner_package') or pkg.name
                rows.append((owner, tblobj.fullname, colname, status, kind))
    return rows


def privacy_report_tsv(rows):  # wf:phase-1:new
    """Return the report rows as TSV text, header line first."""
    return '\n'.join('\t'.join(row) for row in [TSV_HEADER] + rows) + '\n'


def privacy_report_text(rows):  # wf:phase-1:new
    """Return the report rows grouped by table, for reading on a terminal."""
    lines = []
    current_table = None
    for package, table, column, status, kind in rows:
        if table != current_table:
            if lines:
                lines.append('')
            lines.append(table)
            current_table = table
        detail = f' {kind}' if kind else ''
        lines.append(f'  {status:<8}{column}{detail}  [{package}]')
    return '\n'.join(lines) + '\n'
