#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  Created by Davide Paci on 2024-10-21.
#  Copyright (c) 2024 Softwell. All rights reserved.

import lxml.etree as ET
from io import BytesIO

from gnr.lib.services import GnrBaseService
from gnr.core.gnrlang import GnrException
from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method


class Main(GnrBaseService):
    def __init__(self,parent,xsl_path=None, xsl_content=None, **kwargs):
        self.parent = parent
        self.xsl_path = xsl_path
        self.xsl_content = self.xml_transformer()

    def xml_transformer(self):
        with self.parent.storageNode(self.xsl_path).open() as xslt_file:
            xsl_file_content = xslt_file.read()
            xslt_content = BytesIO(xsl_file_content)
        return xslt_content

    def xml_to_html(self, xml, **kwargs):
        if not self.xsl_path:
            raise GnrException('XSL file is missing. Please upload it first.')
        recovering_parser = ET.XMLParser(recover=True)
        xml = bytes(bytearray(xml, encoding = 'utf-8'))
        dom = ET.fromstring(xml, parser=recovering_parser)
        xslt_data = ET.parse(self.xsl_content, parser=recovering_parser)
        transform = ET.XSLT(xslt_data)
        newdom = transform(dom)
        res = ET.tostring(newdom, pretty_print=True)
        return res
    
    
class ServiceParameters(BaseComponent):
    def service_parameters(self,pane,datapath=None,service_name=None,**kwargs):
        fb = pane.formbuilder(datapath=datapath)  
        fb.dropUploader(height='38px', width='152px', label=f'!!Drop file',
                          lbl = '!!Upload XSL file',
                          uploadPath=f'site:services/{service_name}', 
                          ext='xsl',
                          lockScreen=True,
                          progressBar=True,
                          hidden='^.xsl_path',
                          onUploadedMethod=self.onUploadedXsl,
                          rpc_service_name=service_name,
                          rpc_service_type='xmltransform',
                          onResult=f"""
                                genro.publish("floating_message", {{message:"File was uploaded successfully", messageType:"message"}})""")
        fb.lightButton('', _class='iconbox trash', lbl='!!Delete file',
                          hidden='^.xsl_path?=!#v').dataRpc(self.onDeletedXsl, 
                          filepath='=.xsl_path', service_name=service_name,
                          service_type='xmltransform', _ask='!!Confirm deletion?')
        pane.onDbChanges('this.form.reload()', table='sys.service')
        
    @public_method
    def onUploadedXsl(self, file_path=None, service_name=None, service_type=None, **kwargs):
        service_identifier = f"{service_type}_{service_name}"
        with self.db.table('sys.service').recordToUpdate(service_identifier) as sys_rec:
            sys_rec['parameters']['xsl_path'] = file_path
        self.db.commit()
        self.db.table('sys.service').notifyDbUpdate(service_identifier)
        
    @public_method
    def onDeletedXsl(self,filepath=None, service_name=None, service_type=None, **kwargs):
        service_identifier = f"{service_type}_{service_name}"
        self.db.application.site.storageNode(filepath).delete()
        with self.db.table('sys.service').recordToUpdate(service_identifier) as sys_rec:
            sys_rec['parameters']['xsl_path'] = None
        self.db.commit()
        self.db.table('sys.service').notifyDbUpdate(service_identifier)