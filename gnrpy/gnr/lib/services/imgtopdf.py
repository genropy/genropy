#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

import tempfile

from gnr.core.gnrdecorator import extract_kwargs
from gnr.core.gnrlang import  GnrException
from gnr.lib.services import GnrBaseService,BaseServiceType

class ImgToPdfError(GnrException):
    pass
    

class ServiceType(BaseServiceType):
    def conf_imgtopdf(self):
        return dict(implementation='imgtopdf')


class ImgToPdfService(GnrBaseService):
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
    

    @extract_kwargs(pdf=True)
    def imgToPdf(self, srcPath, destPath,**kwargs): #srcPathList per ridurre i processi?

        srcNode = self.parent.storageNode(srcPath)
        destNode = self.parent.storageNode(destPath)
        return self.writePdf(srcNode, destNode,**kwargs)

    def writePdf(self,srcNode, destNode, **kwargs):
        #override
        pass

