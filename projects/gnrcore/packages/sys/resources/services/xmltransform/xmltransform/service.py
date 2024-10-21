#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  Created by Davide Paci on 2024-10-21.
#  Copyright (c) 2024 Softwell. All rights reserved.


from gnr.lib.services import GnrBaseService
import lxml.etree as ET
from gnr.core.gnrlang import GnrException
from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method


class Main(GnrBaseService):
    def __init__(self,parent,xsl_path=None, xsl_content=None, **kwargs):
        self.parent = parent
        self.xsl_path = xsl_path
        self.xsl_content = xsl_content

    def xml_to_html(self, xml):
        if not self.xsl_path:
            raise GnrException('XSL file is missing. Please upload it first.')
        recovering_parser = ET.XMLParser(recover=True)
        xml = bytes(bytearray(xml, encoding = 'utf-8'))
        dom = ET.fromstring(xml, parser=recovering_parser)
        print(x)
        xslt_data = ET.parse(self.xsl_content, parser=recovering_parser)
        transform = ET.XSLT(xslt_data)
        newdom = transform(dom)
        res = ET.tostring(newdom, pretty_print=True)
        return res
    
    
class ServiceParameters(BaseComponent):
    def service_parameters(self,pane,datapath=None,service_name=None,**kwargs):
        fb = pane.formbuilder(datapath=datapath)  
        fb.dropUploader(height='38px', width='76px', label=f'!!Drop file',
                          lbl = '!!Upload XSL file',
                          uploadPath=f'site:services/{service_name}', 
                          ext='xsl',
                          lockScreen=True,
                          progressBar=True,
                          hidden='^.xls_path',
                          onUploadedMethod=self.onUploadedXsl,
                          onResult=f"""
                          genro.publish("floating_message", {{message:"File was uploaded successfully", messageType:"message"}})""")
        fb.lightButton('', _class='iconbox trash', lbl='!!Delete file',
                         hidden='^.xls_path?=!#v').dataRpc(self.onDeletedXsl, filepath='=.xls_path', _ask='!!Confirm deletion?')
        
    @public_method
    def onUploadedXsl(self,file_path=None, **kwargs):
        with self.db.application.site.storageNode(file_path).open() as xslt_file:
            xsl_content = xslt_file.read()
        self.setInClientData(value=file_path, path='sys_service.form.record.parameters.xsl_path')
        self.setInClientData(value=xsl_content, path='sys_service.form.record.parameters.xsl_content')
        
    @public_method
    def onDeletedXsl(self,filepath=None,**kwargs):
        self.parent.storageNode(filepath).delete()
        self.setInClientData(value=None, path='sys_service.form.record.parameters.xsl_path')
        self.setInClientData(value=None, path='sys_service.form.record.parameters.xsl_content')