# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module apphandler.batch : Batch processing and thermo (progress tracking)
# Copyright (c)     : 2004 - 2007 Softwell sas - Milano
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

"""Batch processing and thermo (progress tracking) mixin.

Provides :class:`BatchMixin` — methods for executing batch operations
(optionally forked) and tracking their progress via a thermostat
stored in the page store.

Also provides :class:`BatchExecutor` — a lightweight wrapper around
a page reference used by forked batch processes.
"""

from __future__ import annotations

from typing import Any, Optional

from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import gnrImport
from gnr.core.gnrdecorator import public_method


class BatchMixin:
    """Mixin for batch execution and thermo progress tracking.

    Batch operations can run synchronously or in a forked process.
    Progress is communicated via a ``thermo_<id>`` key in the page
    store, which the client polls through ``rpc_getThermo``.
    """

    def rpc_batchDo(self, batch: str, resultpath: str,
                    forked: bool = False, **kwargs: Any) -> Any:
        """Execute a batch operation.

        Args:
            batch: Identifier in ``"module:ClassName"`` format.
            resultpath: Store path where the result will be written
                (only used in forked mode).
            forked: When ``True`` the batch runs in a separate process.

        Returns:
            The batch result when *forked* is ``False``, otherwise
            ``None`` (the result is written to *resultpath*).

        Note:
            BUG: The ``from processing import Process`` import (line 203
            in original) should be ``from multiprocessing import Process``.
            The ``processing`` module does not exist in modern Python.
        """
        if forked:
            from processing import Process  # BUG: should be ``from multiprocessing import Process``

            p = Process(target=self._batchExecutor, args=(batch, resultpath, forked), kwargs=kwargs)
            p.start()
            return None
        else:
            return self._batchExecutor(batch, resultpath, forked, **kwargs)

    def _batchExecutor(self, batch: str, resultpath: str,
                       forked: bool, **kwargs: Any) -> Any:
        """Locate and run a batch class.

        Args:
            batch: Identifier in ``"module:ClassName"`` format.
            resultpath: Store path for forked results.
            forked: Whether this execution is forked.

        Returns:
            The batch result when not forked.
        """
        batchClass = self._batchFinder(batch)
        batch_instance = batchClass(self.page)
        if forked:
            result = batch_instance.run(**kwargs)
            error = None
            _cls = None
            self.page.setInClientData(resultpath, result, attributes=dict(_error=error, __cls=_cls))
        else:
            return batch_instance.run(**kwargs)

    def _batchFinder(self, batch: str) -> type:
        """Import and return the batch class.

        Args:
            batch: Identifier in ``"module:ClassName"`` format.

        Returns:
            The batch class object.

        Raises:
            Exception: When the module resource cannot be found.
        """
        modName, clsName = batch.split(':')
        modPath = self.page.getResource(modName, 'py') or []
        if modPath:
            m = gnrImport(modPath)
            return getattr(m, clsName)
        else:
            raise Exception('Cannot import component %s' % modName)

    @public_method
    def runSelectionBatch(self, table: str, selectionName: Optional[str] = None,
                          batchFactory: Optional[str] = None, pkeys: Optional[list] = None,
                          thermoId: Optional[str] = None, thermofield: Optional[str] = None,
                          stopOnError: bool = False, forUpdate: bool = False,
                          onRow: Optional[str] = None, **kwargs: Any) -> Any:
        """Execute a batch operation on a frozen selection.

        Args:
            table: Fully qualified table name (``"pkg.table"``).
            selectionName: Name of the frozen selection to use as source.
            batchFactory: Name of the table plugin class that implements
                the batch.  Defaults to ``"batch"``.
            pkeys: Explicit list of primary keys.  When provided,
                *selectionName* is ignored.
            thermoId: Identifier for progress tracking.
            thermofield: Field used as thermo label (``"*"`` for caption).
            stopOnError: Stop at the first error.
            forUpdate: Load records with ``FOR UPDATE`` and commit at end.
            onRow: Optional page method called on each record when no
                *batchFactory* is given.

        Returns:
            The batch result.
        """
        tblobj = self.db.table(table)
        if not pkeys:
            selection = self.page.unfreezeSelection(tblobj, selectionName)
            pkeys = selection.output('pkeylist')

        batch = tblobj.getPlugin(name=batchFactory or 'batch', thermoCb=self.setThermo,
                                 thermoId=thermoId, thermofield=thermofield,
                                 stopOnError=stopOnError, forUpdate=forUpdate, onRow=onRow, **kwargs)
        return batch.run(pkeyList=pkeys)

    def setThermo(self, thermoId: str, progress_1: Optional[int] = None,
                  message_1: Optional[str] = None, maximum_1: Optional[int] = None,
                  command: Optional[str] = None, **kwargs: Any) -> Optional[str]:
        """Update the thermostat (progress indicator) in the page store.

        Args:
            thermoId: Identifier of the thermo to update.
            progress_1: Current progress value.
            message_1: Progress message.
            maximum_1: Maximum progress value.
            command: Control command: ``"init"``, ``"end"``, ``"stopped"``.

        Returns:
            ``"stop"`` if the client requested a stop, otherwise ``None``.

        Note:
            BUG: At line 435 in original, ``command == 'end'`` is a
            comparison (evaluates to bool and discards the result) instead
            of the intended ``command = 'end'`` assignment.  This means
            that when ``prog > max`` the command is never actually set to
            ``'end'``, and the thermo status is not updated to ``'end'``.
        """
        with self.page.pageStore() as store:
            if command == 'init':
                thermoBag = Bag()
            else:
                thermoBag = store.getItem('thermo_%s' % thermoId) or Bag()
            max = maximum_1 or thermoBag['t1.maximum']
            prog = progress_1 or thermoBag['t1.maximum']  # SMELL: reads maximum instead of progress as fallback
            if max and prog > max:
                command == 'end'  # BUG: comparison instead of assignment — should be ``command = 'end'``
            if command == 'end':
                thermoBag['status'] = 'end'
                thermoBag['message'] = '!!Execution completed'
            elif command == 'stopped':
                thermoBag['status'] = 'stopped'
                thermoBag['message'] = '!!Execution stopped'
            else:
                params = dict(progress_1=progress_1, message_1=message_1, maximum_1=maximum_1)
                params.update(kwargs)
                for k, v in list(params.items()):
                    if v is not None:
                        key, thermo = k.split('_')
                        thermoBag['t%s.%s' % (thermo, key)] = v
            store.setItem('thermo_%s' % thermoId, thermoBag)
        if thermoBag['stop']:
            return 'stop'

    def rpc_getThermo(self, thermoId: str, flag: Optional[str] = None) -> Bag:
        """Read or update the thermostat from the page store.

        Args:
            thermoId: Identifier of the thermo.
            flag: When ``"stop"`` the thermo is flagged for stopping.

        Returns:
            The current thermo :class:`Bag`.
        """
        with self.page.pageStore() as store:
            if flag == 'stop':
                thermoBag = store.getItem('thermo_%s' % thermoId) or Bag()
                thermoBag['stop'] = True
                store.setItem('thermo_%s' % thermoId, thermoBag)
            else:
                thermoBag = store.getItem('thermo_%s' % thermoId) or Bag()
        return thermoBag


class BatchExecutor:
    """Lightweight page wrapper for forked batch processes.

    Holds a reference to the page so that batch code running in a
    separate process can still access page utilities.

    Note:
        SMELL: The commented-out ``weakref.ref`` suggests the original
        intent was to use a weak reference, but it was abandoned.  In a
        forked process weak references may not behave as expected.
    """

    def __init__(self, page: Any) -> None:
        self._page = page

    @property
    def page(self) -> Any:
        """Return the page reference."""
        return self._page
