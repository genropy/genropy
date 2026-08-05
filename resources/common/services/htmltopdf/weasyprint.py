# -*- coding: utf-8 -*-

import os
import tempfile
from weasyprint import CSS, HTML

from gnr.lib.services.htmltopdf import HtmlToPdfService

class Service(HtmlToPdfService):
    def writePdf(self,srcPath, destPath,pageSize=None,pageMargin=None,stylesheets=None,
                pdf_kwargs=None, **kwargs):

        srcPath = self.parent.storageNode(srcPath, parent=self.parent)
        page_css = None
        stylesheets = stylesheets or []
        #an explicit pageMargin wins over the sys.pdf_render preference margins
        apply_pref_margins = pageMargin is None
        pref_margins = self.pageMarginsFromPdfKwargs(pdf_kwargs) if apply_pref_margins else {}
        if pageSize:
            pageMargin = pageMargin or 0
            page_css_input=f"""@page {{
                size: {pageSize}; /* Change from the default size of A4 */
                margin: {pageMargin}; /* Set margin on each page */
            }}"""
            stylesheets.append(page_css_input)
        if apply_pref_margins and pref_margins:
            #stylesheets passed to weasyprint are user stylesheets: preference margins need
            #!important to win over the @page margin:0 emitted in the document (author CSS);
            #once at least one side is set in preferences the missing sides default to 0 as
            #plain declarations (symmetric output), beating the weasyprint UA default margin
            #but still losing to margins declared by the document. With no preference margins
            #at all no stylesheet is appended, so raw html without a @page rule of its own
            #(grid pdf export, pagededitor preview) keeps the weasyprint UA default margins
            declarations = []
            for side in ('top','bottom','left','right'):
                if side in pref_margins:
                    declarations.append(f'margin-{side}: {pref_margins[side]} !important;')
                else:
                    declarations.append(f'margin-{side}: 0;')
            stylesheets.append('@page { %s }' % ' '.join(declarations))
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
