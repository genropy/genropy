# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqltable.table : SqlTable — the assembled table class
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

"""SqlTable — the fully assembled database table class.

:class:`SqlTable` inherits from all mixin modules and :class:`GnrObject`,
providing the complete API for operating on a single database table.
"""

from __future__ import annotations

import threading

from gnr.core.gnrlang import GnrObject
from gnr.sql.gnrsqltable_proxy.hierarchical import HierarchicalHandler
from gnr.sql.gnrsqltable_proxy.xtd import XTDHandler

from gnr.sql.gnrsqltable.columns import ColumnsMixin
from gnr.sql.gnrsqltable.query import QueryMixin
from gnr.sql.gnrsqltable.record import RecordMixin
from gnr.sql.gnrsqltable.crud import CrudMixin
from gnr.sql.gnrsqltable.triggers import TriggersMixin
from gnr.sql.gnrsqltable.serialization import SerializationMixin
from gnr.sql.gnrsqltable.copy import CopyMixin
from gnr.sql.gnrsqltable.utils import UtilsMixin


class SqlTable(
    ColumnsMixin,
    QueryMixin,
    RecordMixin,
    CrudMixin,
    TriggersMixin,
    SerializationMixin,
    CopyMixin,
    UtilsMixin,
    GnrObject,
):
    """The base class for database tables.

    Your tables will inherit from it (although it won't be explicit in
    your code, since it's done by GenroPy mixin machinery).

    In your webpage, package or table methods, you can get a reference
    to a table by name::

        self.db.table('packagename.tablename')

    You can also get them from the application instance::

        app = GnrApp('instancename')
        app.db.table('packagename.tablename')
    """

    def __init__(self, tblobj):
        self._model = tblobj
        self.name = tblobj.name
        self.fullname = tblobj.fullname
        self.name_long = tblobj.name_long
        self.name_plural = tblobj.name_plural
        self._user_config = {}
        self._lock = threading.RLock()
        if tblobj.attributes.get('hierarchical'):
            self.hierarchicalHandler = HierarchicalHandler(self)
        if tblobj.attributes.get('xtdtable'):
            self.xtd = XTDHandler(self)

    def use_dbstores(self, **kwargs):
        """Override in package tables to return ``False`` and constrain
        usage to the root dbstore only."""
        pass

    def exception(self, exception, record=None, msg=None, **kwargs):
        """Raise a typed SQL exception.

        :param exception: exception class or string key into ``EXCEPTIONS``
        :param record: the record involved (used for caption)
        :param msg: human-readable error message
        """
        from gnr.sql.gnrsqltable import EXCEPTIONS

        if isinstance(exception, str):
            exception = EXCEPTIONS.get(exception)
            if not exception:
                raise exception  # REVIEW: raises None when key is missing — should raise KeyError or ValueError
        rowcaption = ''
        if record:
            try:
                rowcaption = self.recordCaption(record)
            except Exception:  # REVIEW: bare except — hides real errors in recordCaption
                rowcaption = 'Current Record'
        return exception(
            tablename=self.fullname,
            rowcaption=rowcaption,
            msg=msg,
            localizer=self.db.localizer,
            **kwargs,
        )

    def __repr__(self):
        return "<SqlTable %s>" % repr(self.fullname)

    @property
    def model(self):
        """Return the corresponding ``DbTableObj`` object."""
        return self._model

    @property
    def pkg(self):
        """Return the ``DbPackageObj`` that contains this table."""
        return self.model.pkg

    @property
    def db(self):
        """Return the ``GnrSqlDb`` object."""
        return self.model.db

    dbroot = db
