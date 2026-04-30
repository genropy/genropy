# -*- coding: utf-8 -*-
"""Struct-based equivalent of ``standard_print.tpl``.

Page template used by the ``mako_plugin`` invocation in
``apphandler/export.py:print_standard`` to render a printable HTML
list of a selection.

Composes :class:`HeaderStaticTemplate` (CSS imports only) and
:class:`PrintTableTemplate` (the data table) under a minimal
``<html><head><body>`` shell.
"""

from gnr.web.gnrwebpage_proxy.frontend.basepagetemplate import BasePageTemplate
from gnr.web.gnrwebpage_proxy.frontend.template_lookup import lookup_template_class


class PageTemplate(BasePageTemplate):

    def build(self, builder, arg_dict):
        head = builder.head
        body = builder.body
        meta = arg_dict.get('meta') or {}

        head.meta(http_equiv='content-type', content='text/html; charset=utf-8')

        header_cls = lookup_template_class(self.page.tpldirectories,
                                           'gnr_header_static',
                                           symbol='HeaderStaticTemplate')
        if header_cls is not None:
            header_cls(self.page).render_into(builder, arg_dict)

        head.style(self._table_css_imports())

        head.child('title', content=meta.get('title') or meta.get('header', ''))

        body.attributes['class'] = 'tableWindow %s' % self.page.get_bodyclasses()
        body.child('h1', content=meta.get('header') or meta.get('title', ''),
                   _class='only_print')

        table_cls = lookup_template_class(self.page.tpldirectories,
                                          'standard_print_table',
                                          symbol='PrintTableTemplate')
        if table_cls is not None:
            table_cls(self.page).render_into(
                body, arg_dict,
                columns=arg_dict.get('columns'),
                outdata=arg_dict.get('outdata'),
                colAttrs=arg_dict.get('colAttrs'),
                striped=arg_dict.get('striped'),
            )

    def _table_css_imports(self):
        all_url = self.page.getResourceUri('html_tables/html_tables', 'css')
        print_url = self.page.getResourceUri('html_tables/html_tables_print', 'css')
        lines = []
        if all_url:
            lines.append('@import url("%s") all;' % all_url)
        if print_url:
            lines.append('@import url("%s") print;' % print_url)
        return '\n'.join(lines)
