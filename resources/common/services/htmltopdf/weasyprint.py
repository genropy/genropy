# -*- coding: utf-8 -*-

import os
import tempfile
from weasyprint import CSS, HTML

from gnr.lib.services.htmltopdf import HtmlToPdfService

class Service(HtmlToPdfService):
    def writePdf(self,srcPath, destPath,pageSize=None,pageMargin=None,stylesheets=None, **kwargs):

        srcPath = self.parent.storageNode(srcPath, parent=self.parent)        
        page_css = None
        stylesheets = stylesheets or []
        if pageSize:
            pageMargin = pageMargin or 0
            page_css_input=f"""@page {{
                size: {pageSize}; /* Change from the default size of A4 */
                margin: {pageMargin}; /* Set margin on each page */
            }}"""
            stylesheets.append(page_css_input)
        stylesheets = [CSS(string=css) for css in stylesheets]
        if destPath is None:
            tmp = tempfile.NamedTemporaryFile(prefix='temp', suffix='.pdf',delete=False)
            with srcPath.local_path() as in_path:
                html_doc = HTML(in_path,base_url='.')
                html_doc.write_pdf(target=tmp,stylesheets=stylesheets,presentational_hints=True)
            tmp.seek(0)
            return tmp
        destPath = self.parent.storageNode(destPath, parent=self.parent)
        if destPath.isdir:
            baseName = os.path.splitext(srcPath.basename)[0]
            destPath = destPath.child(f'{baseName}.pdf')
        with srcPath.local_path() as in_path, destPath.local_path() as out_path:
            html_doc = HTML(in_path,base_url='.')
            html_doc.write_pdf(target=out_path,stylesheets=stylesheets,presentational_hints=True)
        return destPath.fullpath.replace('_raw_:', '')
