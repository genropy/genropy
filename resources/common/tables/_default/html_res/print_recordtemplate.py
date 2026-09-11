# -*- coding: utf-8 -*-

# print_recordtemplate.py
# Generic table script to print a single record through a named template resource.
# Copyright (c) Softwell. All rights reserved.

from gnr.web.gnrbaseclasses import TableTemplateToHtml


class Main(TableTemplateToHtml):
    """Print one record of any table through a template chosen by the caller.

    Available to every table via the ``tables/_default`` fallback, so no
    per-template ``html_res`` module is needed. The template name is resolved
    by ``BagToHtmlWeb.contentFromTemplate`` against the script's own table and
    can be given either to the constructor::

        script = page.loadTableScript(table='pkg.mytable',
                                      respath='html_res/print_recordtemplate',
                                      record_template='mytemplate')
        pdfpath = script(record=record_id, pdf=True)

    or at call time, which is what ``callTableScript`` forwards::

        pdfpath = page.callTableScript(table='pkg.mytable',
                                       respath='html_res/print_recordtemplate',
                                       record=record_id, record_template='mytemplate',
                                       pdf=True)
    """
