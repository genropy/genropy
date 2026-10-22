# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module apphandler_next.export : Export, print and PDF operations
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

"""Export, print and PDF mixin.

Provides :class:`ExportMixin` — methods for downloading a generated PDF,
rendering a static grid as an HTML print and running an included view
action.

This module is the copy that receives new work.  The module of the same
name under ``gnr.web.gnrwebpage_proxy.apphandler`` is frozen and is never
imported from here.

The methods with no caller anywhere in the tree are not part of the copy:
``rpc_onSelectionDo``, ``export_standard``, ``print_standard``,
``rpc_pdfmaker`` and ``rpc_printStaticGridDownload``.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method


class ExportMixin:
    """Mixin for export and print operations.

    These methods are invoked from client-side grid actions and produce
    downloadable files or HTML prints.
    """

    def rpc_downloadPDF(self, filename: str, forcedownload: bool = False,
                        **kwargs: Any) -> None:
        """Send a previously generated PDF as an HTTP response.

        Args:
            filename: The PDF filename.
            forcedownload: When ``True`` the browser is forced to
                download rather than display inline.
        """
        response = self.page.response
        response.content_type = "application/pdf"
        if forcedownload:
            response.add_header("Content-Disposition", str("attachment; filename=%s" % filename))
        else:
            response.add_header("Content-Disposition", str("filename=%s" % filename))

        fpath = self.page.pageLocalDocument(filename)
        response.sendfile(fpath)
        os.remove(fpath)

    def _exportFileNameClean(self, filename: Optional[str] = None) -> bytes:
        """Sanitize a filename for export.

        Args:
            filename: Raw filename.  Defaults to the page's maintable
                or request path.

        Returns:
            A cleaned, ASCII-only filename as bytes, truncated to 64
            characters.

        Note:
            SMELL: Returns ``bytes`` (due to ``.encode('ascii', 'ignore')``)
            but callers may expect ``str``.  This can cause type errors
            in Python 3 when concatenating with strings.
        """
        filename = filename or self.page.maintable or self.page.request.path_info.split('/')[-1]
        filename = filename.replace(' ', '_').replace('.', '_').replace('/', '_')[:64]
        filename = filename.encode('ascii', 'ignore')  # SMELL: returns bytes in Python 3
        return filename

    def _getStoreBag(self, storebag: Any) -> Bag:
        """Resolve a store bag from a string identifier or return as-is.

        Args:
            storebag: Either a :class:`Bag`, a ``"gnrsel:pkg.tbl:filename"``
                string, or a path to a local document.

        Returns:
            The resolved :class:`Bag`.

        Note:
            SMELL: The comment ``# da finire`` (``to be finished``)
            indicates this method is incomplete.

            BUG: Uses ``self.unfreezeSelection`` and ``self.pageLocalDocument``
            instead of ``self.page.unfreezeSelection`` and
            ``self.page.pageLocalDocument`` — relies on ``GnrBaseProxy.__getattr__``
            delegation which is fragile and inconsistent with other methods.
        """
        # SMELL: "da finire" — incomplete implementation
        if isinstance(storebag, str):
            if storebag.startswith('gnrsel:'):
                x, tbl, filename = storebag.split(':', 2)
                sel = self.unfreezeSelection(self.app.db.table(tbl), filename)  # BUG: self.app.db — should be self.db
                storebag = sel.output('grid')
            else:
                storebag = Bag(self.pageLocalDocument(storebag))
        return storebag

    def _printCellStyle(self, colAttr: dict[str, Any]) -> str:
        """Extract CSS style string from column attributes.

        Args:
            colAttr: Dictionary of column attributes that may contain
                CSS-like keys (e.g. ``width``, ``color``, ``border``).

        Returns:
            A CSS style string.
        """
        style = [colAttr.get('style')]
        styleAttrNames = ('height', 'width', 'top', 'left', 'right', 'bottom',
                          'visibility', 'overflow', 'float', 'clear', 'display',
                          'z_index', 'border', 'position', 'padding', 'margin',
                          'color', 'white_space', 'vertical_align')

        def isStyleAttr(name: str) -> bool:
            for st in styleAttrNames:
                if name == st or name.startswith('%s_' % st):
                    return True

        for k, v in list(colAttr.items()):
            if isStyleAttr(k):
                style.append('%s: %s;' % (k.replace('_', '-'), v))
        style = ' '.join([v for v in style if v])
        return style

    def rpc_printStaticGrid(self, structbag: Bag, storebag: Any,
                            filename: Optional[str] = None,
                            makotemplate: str = 'standard_print.tpl',
                            **kwargs: Any) -> str:
        """Render a static grid as HTML via Mako and return the URL.

        Args:
            structbag: Grid structure :class:`Bag` (view/row/cell).
            storebag: Grid data (a :class:`Bag` or a string identifier).
            filename: Output filename.
            makotemplate: Mako template path.

        Returns:
            The URL of the generated temporary HTML document.

        Note:
            BUG: The condition ``not filename.lower().endswith('.html') or
            filename.lower().endswith('.htm')`` is logically wrong — it
            should be ``not (filename.lower().endswith('.html') or
            filename.lower().endswith('.htm'))`` (missing parentheses
            around the ``or``).

            SMELL: Opens file with ``open(fpath, 'w')`` but then checks
            ``isinstance(result, str)`` and calls ``.encode('utf-8')`` —
            in Python 3 writing bytes to a text-mode file will fail.
        """
        filename = self._exportFileNameClean(filename)
        if not filename.lower().endswith('.html') or filename.lower().endswith('.htm'):  # BUG: operator precedence
            filename += '.html'
        storebag = self._getStoreBag(storebag)
        columns = []
        colAttrs = {}
        for view in list(structbag.values()):
            for row in list(view.values()):
                for cell in row:
                    col = self.db.colToAs(cell.getAttr('field'))
                    columns.append(col)
                    colAttr = cell.getAttr()
                    dtype = colAttr.get('dtype')
                    if dtype and not ('format' in colAttr):
                        colAttr['format'] = 'auto_%s' % dtype
                    colAttr['style'] = self._printCellStyle(colAttr)
                    colAttrs[col] = colAttr

        outdata = []
        for row in storebag:
            outdata.append(row.getAttr())

        result = self.page.pluginhandler.get_plugin('mako')(mako_path=makotemplate, striped='odd_row,even_row',
                                                            outdata=outdata, colAttrs=colAttrs,
                                                            columns=columns, meta=kwargs)

        fpath = self.page.temporaryDocument(filename)
        f = open(fpath, 'w')
        if isinstance(result, str):
            result = result.encode('utf-8')  # SMELL: writes bytes to text-mode file in Python 3
        f.write(result)
        f.close()
        return self.page.temporaryDocumentUrl(filename)

    @public_method
    def includedViewAction(self, action: Optional[str] = None,
                           export_mode: Optional[str] = None,
                           respath: Optional[str] = None,
                           table: Optional[str] = None,
                           data: Any = None,
                           columns: Optional[str] = None,
                           selectedPkeys: Optional[list] = None,
                           hiddencolumns: Optional[str] = None,
                           selectionName: Optional[str] = None,
                           struct: Any = None,
                           datamode: Optional[str] = None,
                           localized_data: Any = None,
                           downloadAs: Optional[str] = None,
                           selectedRowidx: Optional[list] = None,
                           limit: Optional[int] = None,
                           sortBy: Optional[str] = None,
                           **kwargs: Any) -> Any:
        """Execute an action from an included view (grid export/print).

        Args:
            action: Action identifier (e.g. ``"export"``).
            export_mode: Export format mode.
            respath: Resource path for the action class.  Defaults to
                ``"action/_common/<action>"``.
            table: Fully qualified table name.
            data: Pre-loaded data (when *selectionName* is not used).
            columns: Column specification.
            selectedPkeys: Explicit list of selected primary keys.
            hiddencolumns: Columns to fetch but not display.
            selectionName: Name of the frozen selection.
            struct: Grid structure :class:`Bag`.
            datamode: Data output mode.
            localized_data: Pre-localized data.
            downloadAs: When set, forces download with this filename.
            selectedRowidx: Indices of selected rows.
            limit: Maximum number of rows.
            sortBy: Sort specification.

        Returns:
            The action result (typically a file response).
        """
        page = self.page
        if downloadAs:
            import mimetypes

            page.response.content_type = mimetypes.guess_type(downloadAs)[0]
            page.response.add_header("Content-Disposition", str("attachment; filename=%s" % downloadAs))
        if not respath:
            respath = 'action/_common/%s' % action
        res_obj = self.page.site.loadTableScript(page=self.page, table=table, respath=respath, class_name='Main')
        if selectionName:
            data = self.page.getUserSelection(selectionName=selectionName, selectedRowidx=selectedRowidx,
                                              limit=limit, sortBy=sortBy)
        elif selectedPkeys and columns:
            query_columns = [columns]
            if hiddencolumns:
                query_columns.append(hiddencolumns)
                res_obj.hiddencolumns = hiddencolumns.split(',')
            res_obj.selectedPkeys = selectedPkeys
            data = res_obj.get_selection(columns=','.join(query_columns))
        return res_obj.gridcall(data=data, struct=struct, export_mode=export_mode,
                                localized_data=localized_data, datamode=datamode,
                                selectedRowidx=selectedRowidx, filename=downloadAs, table=table, **kwargs)
