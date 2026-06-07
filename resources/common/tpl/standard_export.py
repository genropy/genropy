# -*- coding: utf-8 -*-
"""Python equivalent of ``standard_export.tpl``.

Page template used to render an exportable HTML view of a selection.
Iterates over ``selection.allColumns`` and emits a transparent-styled
table suitable for spreadsheet copy-paste.
"""

from gnr.web.gnrwebpage_proxy.frontend.basepagetemplate import BasePageTemplate


class PageTemplate(BasePageTemplate):

    def build(self, builder, arg_dict):
        head = builder.head
        body = builder.body

        head.child('meta', _attributes={'http-equiv': 'content-type'},
                   _content='text/html; charset=utf-8')
        head.child('title', content=arg_dict.get('title', ''))
        head.child('style',
                   content='body{background-color: transparent;}'
                           'table{background-color: transparent;}',
                   _type='text/css')

        body.child('h1', content=arg_dict.get('header', ''))

        selection = arg_dict.get('selection')
        columns = arg_dict.get('columns')
        if not columns and selection is not None:
            columns = [c for c in selection.allColumns
                       if c not in ('pkey', 'rowidx')]
        outdata = selection.output('dictlist', columns=columns,
                                   asIterator=True) if selection else []
        col_attrs = selection.colAttrs if selection else {}

        translate = self.page._
        fmt = self.page.toText

        table = body.child('table', border='1px')
        thead = table.child('thead')
        tr = thead.child('tr')
        for colname in columns or []:
            attr = col_attrs.get(colname, {})
            tr.child('th', content=translate(attr.get('label', colname)))

        tbody = table.child('tbody')
        for row in outdata:
            tr = tbody.child('tr')
            for colname in columns or []:
                attr = col_attrs.get(colname, {})
                value = fmt(row[colname],
                            format=attr.get('format'),
                            mask=attr.get('mask'))
                value = value.replace('\n', ' ').replace('<br />', ' ')
                tr.child('td', content=value)
