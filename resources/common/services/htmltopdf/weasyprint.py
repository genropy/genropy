# -*- coding: utf-8 -*-

import os
from gnr.lib.services.htmltopdf import HtmlToPdfService,HtmlToPdfError

class Service(HtmlToPdfService):
    def writePdf(self,srcPath, destPath,pageSize=None,pageMargin=None,stylesheets=None, **kwargs):
        from weasyprint import CSS, HTML
        srcPath = self.parent.storageNode(srcPath, parent=self.parent)
        destPath = self.parent.storageNode(destPath, parent=self.parent)
        page_css = None
        stylesheets = stylesheets or []
        if pageSize:
            pageMargin = pageMargin or 0
            page_css_input=f"""@page {{
                size: {pageSize}; /* Change from the default size of A4 */
                margin: {pageMargin}; /* Set margin on each page */
            }}"""
            stylesheets.append(page_css_input)
        if destPath.isdir:
            baseName = os.path.splitext(srcPath.basename)[0]
            destPath = destPath.child(f'{baseName}.pdf')
        with srcPath.local_path() as in_path, destPath.local_path() as out_path:
            html_doc = HTML(in_path,base_url='.')
            stylesheets = [CSS(string=css) for css in stylesheets]
            html_doc.write_pdf(target=out_path,stylesheets=stylesheets,presentational_hints=True)
        return destPath.fullpath.replace('_raw_:', '')