# -*- coding: utf-8 -*-
"""Struct-based equivalent of ``standard_print_table.tpl``.

Sub-template that renders a single ``<table>`` from *columns*, *outdata*,
*colAttrs*. Used by ``standard_print`` for the printable list page.
"""

from gnr.web.gnrwebpage_proxy.frontend.basepagetemplate import BasePageTemplate


class PrintTableTemplate(BasePageTemplate):

    def render_into(self, parent, arg_dict, columns=None, outdata=None,
                    colAttrs=None, striped=None):
        translate = self.page._
        fmt = self.page.toText
        col_attrs = colAttrs or {}

        table = parent.table(_class='full_page', id='maintable')
        thead = table.thead()
        tr = thead.tr()
        for colname in columns or []:
            attr = col_attrs.get(colname, {})
            tr.th(translate(attr.get('name', colname)),
                  style=attr.get('style', ''))

        tbody = table.tbody()
        for row in outdata or []:
            row_class = next(striped) if striped is not None else ''
            tr = tbody.tr(_class=row_class)
            for colname in columns or []:
                attr = col_attrs.get(colname, {})
                tr.td(fmt(row.get(colname),
                          format=attr.get('format'),
                          mask=attr.get('mask'),
                          dtype=attr.get('dtype')),
                      _class='dtype_%s' % attr.get('dtype', 'T'),
                      colname=colname,
                      style=attr.get('style', ''))
