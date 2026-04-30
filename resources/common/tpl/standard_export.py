# -*- coding: utf-8 -*-
"""Struct-based equivalent of ``standard_export.tpl``.

Page template used to render an exportable HTML view of a selection.
Iterates over ``selection.allColumns`` (when no explicit *columns* are
given) and emits a transparent-styled ``<table>`` suitable for being
copied into a spreadsheet.
"""

from gnr.web.gnrwebpage_proxy.frontend.basepagetemplate import BasePageTemplate


class PageTemplate(BasePageTemplate):

    def build(self, builder, arg_dict):
        head = builder.head
        body = builder.body

        head.meta(http_equiv='content-type', content='text/html; charset=utf-8')
        head.child('title', content=arg_dict.get('title', ''))
        head.style('body{background-color: transparent;}'
                   'table{background-color: transparent;}',
                   title='text/css')

        body.child('h1', content=arg_dict.get('header', ''))

        selection = arg_dict.get('selection')
        columns = arg_dict.get('columns')
        if not columns and selection is not None:
            columns = [c for c in selection.allColumns if c not in ('pkey', 'rowidx')]
        outdata = selection.output('dictlist', columns=columns,
                                   asIterator=True) if selection else []
        col_attrs = selection.colAttrs if selection else {}

        translate = self.page._
        fmt = self.page.toText

        table = body.table(border='1px')
        thead = table.thead()
        tr = thead.tr()
        for colname in columns or []:
            attr = col_attrs.get(colname, {})
            tr.th(translate(attr.get('label', colname)))

        tbody = table.tbody()
        for row in outdata:
            tr = tbody.tr()
            for colname in columns or []:
                attr = col_attrs.get(colname, {})
                value = fmt(row[colname],
                            format=attr.get('format'),
                            mask=attr.get('mask'))
                value = value.replace('\n', ' ').replace('<br />', ' ')
                tr.td(value)
