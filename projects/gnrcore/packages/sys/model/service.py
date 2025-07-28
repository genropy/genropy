# encoding: utf-8

import os
from datetime import datetime

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('service', name_long='!!Service', 
                    name_plural='!!Services',caption_field='service_identifier',
                    pkey='service_identifier',
                    pkey_columns='service_type,service_name')
        self.sysFields(tbl,id=False)
        tbl.column('service_identifier', size=':60', name_long='!!Identifier')
        tbl.column('service_type', size=':30', name_long='!!Service type')
        tbl.column('service_name', size=':30', name_long='!!Service name') #service_name
        tbl.column('implementation', name_long='!!Implementation')
        tbl.column('parameters', dtype='X', name_long='!!Parameters')
        tbl.column('daemon', dtype='B', name_long='!!Daemon')
        tbl.column('disabled', dtype='B', name_long='!!Disabled')


    @public_method
    def getAvailableServiceTree(self, _querystring=None,**kwargs):
        result = Bag()
        page = self.db.currentPage
        site = self.db.application.site
        resdirs = site.resource_loader.getResourceList(page.resourceDirs,'services')
        for service_root in resdirs:
            service_types = os.listdir(service_root)
            for service_type in service_types:
                stypedir = os.path.join(service_root,service_type)
                if not os.path.isdir(stypedir):
                    continue
                for resource in os.listdir(stypedir):
                    resname,ext = os.path.splitext(resource)
                    if resname.startswith('.') or resname=='_base_' or resname=='__pycache__':
                        continue
                    resource = resname
                    respath = os.path.join(service_root,service_type,resource)
                    if os.path.isdir(respath):
                        resource = os.path.join(resname,'service')
                    elif ext!='.py':
                        continue
                    if _querystring!='*':
                        chunk = _querystring.replace('*','').lower()
                        if not chunk in service_type and not chunk in resname:
                            print('continue',service_type,resname)
                            continue
                    result.addItem(service_type,resource,implementation=resource,service_type=service_type,
                                        default_kw=dict(implementation=resource,service_type=service_type),
                                        _pkey=service_type, caption=f"{service_type} - {resname}")
        return result.sort(),dict(columns='service_type,implementation', headers='Service type,Implementation')

    def addService(self,service_type=None,service_name=None,implementation=None,**kwargs):
        parameters = Bag(kwargs)
        record = self.newrecord(service_type=service_type,service_name=service_name,implementation=implementation,
                                parameters=parameters)
        self.insert(record)
        return record

    def serviceExpiredTs(self,record=None):
        site = getattr(self.db.application,'site',None)
        if site:
            with site.register.globalStore() as gs:
                gs.setItem('globalServices_lastChangedConfigTS.%(service_identifier)s' %record,datetime.now())

    def trigger_onUpdated(self,record,old_record=None):
        self.serviceExpiredTs(record)

    def trigger_onDeleted(self,record):
        self.serviceExpiredTs(record)
