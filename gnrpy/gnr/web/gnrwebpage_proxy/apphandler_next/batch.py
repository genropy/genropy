# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module apphandler_next.batch : Batch processing and thermo (progress tracking)
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

"""Batch processing and thermo (progress tracking) mixin.

Provides :class:`BatchMixin` — the batch class lookup and the batch
executor.

Also provides :class:`BatchExecutor` — a lightweight wrapper around
a page reference used by forked batch processes.

This module is the copy that receives new work.  The module of the same
name under ``gnr.web.gnrwebpage_proxy.apphandler`` is frozen and is never
imported from here.

The methods with no caller anywhere in the tree are not part of the copy:
``rpc_batchDo``, ``runSelectionBatch``, ``setThermo`` and ``rpc_getThermo``.
"""

from __future__ import annotations

from typing import Any

from gnr.core.gnrlang import gnrImport


class BatchMixin:
    """Mixin for batch execution.

    ``_batchExecutor`` runs a batch class resolved by ``_batchFinder``;
    a forked run writes its result to the page store.
    """

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
