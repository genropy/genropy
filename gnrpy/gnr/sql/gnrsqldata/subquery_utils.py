#-*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqldata.subquery_utils : Subquery dict normalization
# Copyright (c) : 2004 - 2026 Softwell srl - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU.
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import re

_THIS_RE = re.compile(r'(@[\w.]+|\$\w+)\s*=\s*#THIS\.(\w+)(.*)', re.DOTALL)


def normalize_subquery_dict(sq_pars):
    """Normalize a subquery dict from legacy to canonical syntax.

    Converts the old ``where='$fk=#THIS.field AND extra'`` form into
    the explicit ``join_to`` / ``join_from`` / ``join_condition`` fields.

    The dict is modified **in-place**.

    Rules:
    - If ``join_to`` is already present the dict is left untouched
      (new syntax, noop).
    - If ``where`` contains ``#THIS``, it is split into:
      - ``join_to``: the FK column in the subquery table (e.g. ``$customer_id``)
      - ``join_from``: the field on the main table (e.g. ``id``)
      - ``join_condition``: any residual filter after ``AND`` (or ``None``)
      - ``where`` is removed from the dict.
    - If ``where`` does not contain ``#THIS`` the dict is left untouched
      (uncorrelated subquery).
    """
    if 'join_to' in sq_pars:
        return

    sq_where = sq_pars.get('where', '')
    if not sq_where or '#THIS' not in sq_where:
        return

    m = _THIS_RE.match(sq_where)
    if not m:
        return

    sq_pars['join_to'] = m.group(1)
    sq_pars['join_from'] = m.group(2)

    residual = m.group(3).strip()
    if residual.upper().startswith('AND '):
        residual = residual[4:].strip()

    sq_pars['join_condition'] = residual or None
    del sq_pars['where']
