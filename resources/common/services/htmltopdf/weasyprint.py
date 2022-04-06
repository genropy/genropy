#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

from builtins import str
import os
from weasyprint import CSS, HTML
from gnr.lib.services.htmltopdf import HtmlToPdfService,HtmlToPdfError

class Service(HtmlToPdfService):
    def writePdf(self,srcPath, destPath, orientation=None, page_height=None, page_width=None,
                        pdf_kwargs=None,htmlTemplate=None,bodyStyle=None,**kwargs):
        srcPath = self.parent.storageNode(srcPath, parent=self.parent)
        destPath = self.parent.storageNode(destPath, parent=self.parent)

        page_css_input="""@page {
        size: A4; /* Change from the default size of A4 */
        margin: 0.25cm; /* Set margin on each page */
        }"""
        print('uso weasyprint')

        if destPath.isdir:
            baseName = os.path.splitext(srcPath.basename)[0]
            destPath = destPath.child('%s.pdf' % baseName)
        page_css = CSS(string=page_css_input)
        with srcPath.local_path() as in_path, destPath.local_path() as out_path:
            html_doc = HTML(in_path)
            html_doc.write_pdf(target=out_path, stylesheets=[page_css])
        return destPath.fullpath.replace('_raw_:', '')