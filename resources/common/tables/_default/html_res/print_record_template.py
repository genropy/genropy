# -*- coding: utf-8 -*-

# print_record_template.py
# Generic table script to print a single record through a named template resource.
# Copyright (c) Softwell. All rights reserved.

from gnr.web.gnrbaseclasses import TableTemplateToHtml


class Main(TableTemplateToHtml):
    """Print one record of any table through a template chosen by the caller.

    Available to every table via the ``tables/_default`` fallback, so no
    per-template ``html_res`` module is needed. The template name is passed to
    the constructor as ``record_template`` and resolved by
    ``BagToHtmlWeb.contentFromTemplate`` against the script's own table::

        script = page.loadTableScript(table='pkg.mytable',
                                      respath='html_res/print_record_template',
                                      record_template='mytemplate')
        pdfpath = script(record=record_id, pdf=True)
    """
