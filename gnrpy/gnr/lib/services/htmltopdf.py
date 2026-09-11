#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

import os
import re
import tempfile
from datetime import datetime, date

from gnr.core.gnrdecorator import extract_kwargs
from gnr.core.gnrlang import  GnrException
from gnr.lib.services import GnrBaseService,BaseServiceType
from gnr.lib.services.storage import StorageNode

#a valid margin: non-negative number with an optional css length unit (bare number -> mm)
CSS_LENGTH_RE = re.compile(r'^(?:\d+(?:\.\d+)?|\.\d+)(?P<unit>mm|cm|in|px|pt|pc|em|rem|%)?$')


class HtmlToPdfError(GnrException):
    pass

class ServiceType(BaseServiceType):
    def conf_htmltopdf(self):
        try:
            import weasyprint
            pdf_pref = self.site.getPreference('.pdf_render',pkg='sys') if self.site else None
            pdf_pref = pdf_pref or {}
            legacy_mode = pdf_pref.get('wk_legacy')
            if legacy_mode:
                weasyprint = False
        except ImportError:
            weasyprint = False
        default_implementation = 'weasyprint' if weasyprint else 'wk'
        return dict(implementation=default_implementation)


class HtmlToPdfService(GnrBaseService):
    def __init__(self,parent,**kwargs):
        self.parent = parent

    def printBodyStyle(self):
        return "font-size:12px;font-family: Arial, Verdana, sans-serif;margin-top:0;margin-bottom:0;margin-left:0;margin-right:0;-webkit-text-size-adjust:auto;"

    def standardPageHtmlTemplate(self,bodyStyle=None):
        bodyStyle = bodyStyle or self.printBodyStyle()
        head ="""<head> 
                    <meta http-equiv="Content-Type" content="text/html; charset=utf-8"> 
                    <style> 
                        .gnrlayout{position:absolute;} 
                        body{%s}
                        .letterhead_page{page-break-before:always;} 
                        .letterhead_page:first-child{page-break-before:avoid;}
                    </style>
                </head>
                     """%bodyStyle
        body = "<body>%s</body>"
        return """<html> 
                    %s 
                    %s
                 </html>""" %(head,body)

    def createTempHtmlFile(self,htmlText,htmlTemplate=None,bodyStyle=None):
        if not '<html' in htmlText:
            htmlTemplate = htmlTemplate or self.standardPageHtmlTemplate(bodyStyle)
            htmlText = htmlTemplate %htmlText
        tmp = tempfile.NamedTemporaryFile(prefix='temp', suffix='.html',delete=False)
        tmp.write(htmlText.encode())
        url = tmp.name
        tmp.close()
        return url

    def pageMarginsFromPdfKwargs(self, pdf_kwargs=None):
        """Extract ``margin_top/bottom/left/right`` from pdf_kwargs as CSS lengths.

        Values are normalized before validation: internal whitespace is removed
        (``'10 mm'`` -> ``'10mm'``) and a decimal comma becomes a dot
        (``'1,5'`` -> ``'1.5'``). Bare non-negative numbers get the ``mm`` unit
        (wkhtmltopdf's implicit unit, so stored preference values keep their
        meaning); numbers with an explicit css length unit (mm, cm, in, px, pt,
        pc, em, rem, %) are kept as normalized. Anything else (negative numbers,
        unknown units, garbage) skips the side entirely, as if it were unset: an
        invalid value interpolated in the generated stylesheet would be dropped
        by the renderer, leaving that side silently asymmetric.

        :param pdf_kwargs: dict possibly holding ``margin_*`` entries
        :returns: dict keyed by side (``top``, ``bottom``, ``left``, ``right``)"""
        pdf_kwargs = pdf_kwargs or {}
        margins = {}
        for side in ('top', 'bottom', 'left', 'right'):
            value = pdf_kwargs.get('margin_%s' % side)
            if value is None or isinstance(value, bool):
                continue
            #remove internal whitespace and normalize a decimal comma to a dot
            value = ''.join(str(value).split()).replace(',', '.')
            match = CSS_LENGTH_RE.match(value)
            if not match:
                continue
            if not match.group('unit'):
                value = '%smm' % value
            margins[side] = value
        return margins

    @extract_kwargs(pdf=True)
    def htmlToPdf(self, srcPath, destPath=None, orientation=None, page_height=None,
                page_width=None, pdf_kwargs=None,htmlTemplate=None,bodyStyle=None,**kwargs): #srcPathList per ridurre i processi?
            
        """TODO
        
        :param src_path: TODO
        :param destPath: TODO
        :param orientation: TODO"""

       #if not destPath:
       #    destPath = 'temp:tempfile.pdf'


        if not isinstance(srcPath, StorageNode) and '<' in srcPath:
            srcPath = self.createTempHtmlFile(srcPath,htmlTemplate=htmlTemplate,bodyStyle=bodyStyle)
            pdf_path = self.htmlToPdf(srcPath,destPath,orientation,pdf_kwargs=pdf_kwargs,**kwargs)
            os.remove(srcPath)
            return pdf_path
        srcNode = self.parent.storageNode(srcPath)
        pdf_pref = self.parent.getPreference('.pdf_render',pkg='sys') if self.parent else None
        #preference should be in sys.service service_parameters
        keep_html = False
        if pdf_pref:
            pdf_pref = pdf_pref.asDict(ascii=True)
            keep_html = pdf_pref.pop('keep_html', False)
            wk_legacy = pdf_pref.pop('wk_legacy', False)
            use_wkhtmltopdf = pdf_pref.pop('use_wkhtmltopdf', False)
            pdf_kwargs = pdf_kwargs or dict()
            pdf_pref.update(pdf_kwargs)
            pdf_kwargs = pdf_pref
        if keep_html:

            now = datetime.now()
            sn = self.parent.storageNode(destPath) if destPath else srcNode
            baseName = sn.cleanbasename
            debugName = "%s_%02i_%02i_%02i.html"%(baseName, now.hour,now.minute,now.second)
            htmlfilenode = self.parent.storageNode('site:print_debug',
                date.today().isoformat(), debugName ,autocreate=-1)
            srcNode.copy(htmlfilenode)
        
        return self.writePdf(srcPath, destPath, orientation=orientation, page_height=page_height, 
                    page_width=page_width, pdf_kwargs=pdf_kwargs,
                    htmlTemplate=htmlTemplate,bodyStyle=bodyStyle,**kwargs)
    
    def writePdf(self,srcPath, destPath, orientation=None, page_height=None, page_width=None, 
                        pdf_kwargs=None,htmlTemplate=None,bodyStyle=None,**kwargs):
        #override
        pass

