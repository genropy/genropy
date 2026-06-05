# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqltable.columns : Column access, properties and variant columns
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

"""Column access, model properties and variant column generators.

Provides :class:`ColumnsMixin` — a mixin for :class:`~gnrsqltable.table.SqlTable`
that exposes table metadata (columns, relations, properties) and the
``variantColumn_*`` family of virtual-column generators.
"""

from __future__ import annotations

import re
from datetime import datetime

from gnr.core import gnrstring
from gnr.core.gnrlang import uniquify
from gnr.core.gnrdict import dictExtract
from gnr.sql._typing import SqlTableBaseMixin


class ColumnsMixin(SqlTableBaseMixin):
    """Column access, model delegation and variant column generators."""

    # ------------------------------------------------------------------
    #  Column / relation access
    # ------------------------------------------------------------------

    def column(self, name, **kwargs):
        """Return a column object by *name* or relation path.

        :param name: column name or relation path (e.g. ``@director_id.name``)
        """
        result = self.model.column(name, **kwargs)
        return result

    def subtable(self, name, **kwargs):
        """Return a subtable object by *name*.

        :param name: subtable name or relation path
        """
        result = self.model.subtable(name, **kwargs)
        return result

    def fullRelationPath(self, name):
        """Return the fully qualified relation path for *name*."""
        return self.model.fullRelationPath(name)

    # ------------------------------------------------------------------
    #  Partition
    # ------------------------------------------------------------------

    def getPartitionCondition(self, ignorePartition=None):
        if ignorePartition:
            return
        partitionParameters = self.partitionParameters
        if partitionParameters:
            env = self.db.currentEnv
            if env.get('current_%(path)s' % partitionParameters):
                return "$%(field)s =:env_current_%(path)s" % partitionParameters
            elif env.get('allowed_%(path)s' % partitionParameters):
                return (
                    "( $%(field)s IS NULL OR $%(field)s IN :env_allowed_%(path)s )"
                    % partitionParameters
                )
            else:
                partitionColumn = self.column(partitionParameters["field"])
                relation_path = (
                    getattr(partitionColumn, 'relation_path', None)
                    or partitionParameters["field"]
                )
                allowedPartitionField = [
                    f'@{c}' if not c.startswith('@') else c
                    for c in relation_path.split('.')
                ] + ['__allowed_partition']
                allowedPartitionField = '.'.join(allowedPartitionField)
                try:
                    allowedPartitionColumn = self.column(allowedPartitionField)
                except Exception:  # REVIEW: bare except — should catch specific column-lookup errors
                    allowedPartitionColumn = None
                if allowedPartitionColumn is not None:
                    return f'{allowedPartitionField} IS TRUE'

    @property
    def partitionParameters(self):
        kw = dictExtract(self.attributes, 'partition_')
        if not kw:
            return
        result = dict()
        result['field'] = list(kw.keys())[0]  # REVIEW: assumes kw is non-empty — guarded by early return but fragile
        result['path'] = kw[result['field']]
        col = self.column(result['field'])
        if col.relatedColumn() is None:
            result['table'] = self.fullname
        else:
            result['table'] = col.relatedColumn().table.fullname
        return result

    # ------------------------------------------------------------------
    #  User configuration
    # ------------------------------------------------------------------

    @property
    def user_config(self):
        uc = self._user_config
        if not uc:
            self._user_config = {'ts': datetime.now(), 'config': {}}
        else:
            expirebag = self.db.currentEnv.get('_user_conf_expirebag')
            if expirebag:
                exp_ts = (
                    expirebag[self.fullname]
                    or expirebag['%s.*' % self.pkg.name]
                    or expirebag['*']
                )
                if exp_ts and exp_ts > uc['ts']:
                    self._user_config = {'ts': datetime.now(), 'config': {}}
        return self._user_config['config']

    def getUserConfiguration(self, user_group=None, user=None):
        user_config = self.user_config.get((user_group, user))
        if user_config is None:
            with self._lock:
                user_config = self.db._getUserConfiguration(
                    table=self.fullname, user_group=user_group, user=user,
                )
                self.user_config[(user_group, user)] = user_config or False
        return user_config

    # ------------------------------------------------------------------
    #  Column print width
    # ------------------------------------------------------------------

    def getColumnPrintWidth(self, column):
        """Compute the correct printing width for *column*."""
        if column.dtype in ['A', 'C', 'T', 'X', 'P']:
            size = column.attributes.get('size', None)
            values = column.attributes.get('values', None)
            if values or not size:
                if column.dtype == 'T':
                    result = 20
                else:
                    result = 12
            elif isinstance(size, str):
                if ':' in size:
                    size = size.split(':')[1]
                size = float(size)
                if size < 3:
                    result = 2
                elif size < 10:
                    result = size * 0.8
                elif size < 30:
                    result = size * 0.7
                else:
                    result = 30
            else:
                result = size
        else:
            result = gnrstring.guessLen(
                column.dtype,
                format=column.attributes.get('print_format', None),
                mask=column.attributes.get('print_mask', None),
            )
        namelong = (
            column.attributes.get('name_short')
            or column.attributes.get('name_long', 'untitled')
        )
        namelong = namelong.replace('!!', '')
        if '\n' in namelong:
            namelong = namelong.split('\n')
            nl = [len(x) for x in namelong]
            headerlen = max(nl)
        else:
            headerlen = len(namelong)
        return max(result, headerlen)

    # ------------------------------------------------------------------
    #  Model-delegated properties
    # ------------------------------------------------------------------

    @property
    def attributes(self):
        """Table attributes dictionary."""
        return self.model.attributes

    @property
    def pkey(self):
        """Primary key field name."""
        return self.model.pkey

    @property
    def pkeys(self):
        """Composite primary key field names."""
        return self.model.pkeys

    @property
    def lastTS(self):
        """Last-modified timestamp field name."""
        return self.model.lastTS

    @property
    def logicalDeletionField(self):
        """Logical deletion field name (or ``None``)."""
        return self.model.logicalDeletionField

    @property
    def multidb(self):
        return self.attributes.get('multidb', None)

    @property
    def multi_tenant(self):
        return self.model.multi_tenant

    @property
    def draftField(self):
        """Draft field name (or ``None``)."""
        return self.model.draftField

    @property
    def noChangeMerge(self):
        """Whether change-merge is disabled for this table."""
        return self.model.noChangeMerge

    @property
    def rowcaption(self):
        """The table's rowcaption template string."""
        return self.model.rowcaption

    @property
    def newrecord_caption(self):
        """Caption for a new (unsaved) record."""
        return self.model.newrecord_caption

    @property
    def columns(self):
        """Column list object (``DbColumnListObj``)."""
        return self.model.columns

    @property
    def virtual_columns(self):
        """Virtual column list object."""
        return self.model.virtual_columns

    @property
    def relations(self):
        """All relations (columns + relations) Bag."""
        return self.model.relations

    @property
    def indexes(self):
        """Index list object."""
        return self.model.indexes

    @property
    def relations_one(self):
        """Bag of outgoing (many-to-one) relations."""
        return self.model.relations_one

    @property
    def relations_many(self):
        """Bag of incoming (one-to-many) relations."""
        return self.model.relations_many

    # ------------------------------------------------------------------
    #  Misc column helpers
    # ------------------------------------------------------------------

    def removeLocalizationFromText(self, text):
        return re.sub("(?:!!)(?:\\[\\w*\\])?(.*)", "\\1", text)

    def counterColumns(self):
        return

    # ------------------------------------------------------------------
    #  Variant column generators
    # ------------------------------------------------------------------

    def variantColumn_unaccent(self, field, **kwargs):
        sql_formula = self.db.adapter.unaccentFormula(field)
        return dict(
            name='{field}_unaccent'.format(field=field),
            sql_formula=sql_formula,
            **kwargs,
        )

    def variantColumn_fill(self, field, side='r', size=0, char='_', **kwargs):
        sql_formula = "{side}pad(${field},{size},'{char}')".format(
            side=side, field=field, size=size, char=char,
        )
        return dict(
            name='{field}_{side}filled'.format(field=field, side=side),
            sql_formula=sql_formula,
            **kwargs,
        )

    def variantColumn_captions(self, field, related_table=None,
                               caption_field=None, sep=None, order_by=None,
                               **kwargs):
        reltableobj = self.db.table(related_table)
        caption_field = (
            caption_field or reltableobj.attributes.get('caption_field')
        )
        sep = sep or ','
        order_by = (
            order_by
            or reltableobj.attributes.get('order_by')
            or f'${reltableobj.pkey}'
        )
        where = (
            f"${reltableobj.pkey} = "
            f"ANY(string_to_array(#THIS.{field},'{sep}'))"
        )
        return dict(
            name=f'{field}_captions',
            sql_formula=f"array_to_string(ARRAY(#captions),'{sep}')",
            select_captions=dict(
                table=related_table,
                columns=f'${caption_field}',
                where=where,
                order_by=order_by,
            ),
            **kwargs,
        )

    def variantColumn_masked(self, field, mode='2-4', placeholder='*',
                             **kwargs):
        """Create a masked version of a field for secure display.

        :param field: field name to mask
        :param mode: masking mode — ``'email'``, ``'creditcard'``,
            ``'phone'``, or ``'N-M'`` format (visible chars at start/end)
        :param placeholder: masking character (default ``'*'``)
        """
        field_ref = f'${field}'
        sql_formula = self.db.adapter.mask_field_sql(
            field_ref, mode=mode, placeholder=placeholder,
        )
        if 'name_long' in kwargs:
            kwargs['name_long'] = f"{kwargs['name_long']} (masked)"
        return dict(
            name=f'{field}_masked',
            sql_formula=sql_formula,
            dtype='T',
            **kwargs,
        )

    def variantColumn_egvariant(self, field, **kwargs):
        # for documentation
        pass

    def variantColumn_age_day(self, field, dateArg=None, **kwargs):
        sql_formula = self.db.adapter.ageAtDate(
            field, dateArg=dateArg, timeUnit='day',
        )
        return dict(
            name='{field}_age_day'.format(field=field),
            sql_formula=sql_formula,
            dtype='L',
            **kwargs,
        )

    def variantColumn_age(self, field, dateArg=None, **kwargs):
        dref = dateArg or ':env_workdate'
        return dict(
            name='{field}_age'.format(field=field),
            dtype='T',
            sql_formula='CAST(age(${field},{dref}) as TEXT)'.format(
                field=field, dref=dref,
            ),
            **kwargs,
        )

    def variantColumn_sharevalue(self, field, sharefield=None, **kwargs):
        result = []
        f = self.query(
            columns='{sharefield} AS _shval'.format(sharefield=sharefield),
            distinct=True,
        ).fetch()
        for r in f:
            shval = r['_shval']
            sql_formula = (
                "(CASE WHEN {sharefield} ='{shval}' "
                "THEN ${field} ELSE 0 END)"
            ).format(sharefield=sharefield, shval=shval, field=field)
            result.append(dict(
                name='{field}_{shval}'.format(field=field, shval=shval),
                sql_formula=sql_formula,
                var_shval=shval,
                dtype='N',
            ))
        return result

    # ------------------------------------------------------------------
    #  Permissions
    # ------------------------------------------------------------------

    @property
    def availablePermissions(self):
        default_table_permissions = [
            'ins', 'upd', 'del', 'archive', 'export', 'import',
            'print', 'mail', 'action', 'configure_view',
        ]
        if not hasattr(self, '_availablePermissions'):
            customPermissions = dict()
            for pkgid, pkgobj in list(self.db.packages.items()):
                customPermissions.update(
                    dictExtract(pkgobj.attributes, 'permission_'),
                )
            customPermissions.update(
                dictExtract(self.attributes, 'permission_'),
            )
            customPermissions = (
                default_table_permissions + list(customPermissions.keys())
            )
            for k, handler in list(self.__dict__.items()):
                permissions = getattr(handler, 'permissions', None)
                if permissions:
                    customPermissions = (
                        customPermissions + permissions.split(',')
                    )
            self._availablePermissions = ','.join(
                uniquify(customPermissions),
            )
        return self._availablePermissions

    # ------------------------------------------------------------------
    #  Real columns helper
    # ------------------------------------------------------------------

    @property
    def real_columns(self) -> str:
        """Precomputed ``$col1,$col2,...`` string of all real columns."""
        return ','.join(f'${c}' for c in self.columns)

    def baseViewColumns(self):
        """Return a comma-separated string of columns marked as base view."""
        allcolumns = self.model.columns
        result = [
            k for k, v in list(allcolumns.items())
            if v.attributes.get('base_view')
        ]
        if not result:
            result = [
                col for col, colobj in list(allcolumns.items())
                if not colobj.isReserved
            ]
        return ','.join(result)
