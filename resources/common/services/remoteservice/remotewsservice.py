# -*- coding: utf-8 -*-

from gnr.lib.services.remoteservice import RemoteService
from gnr.web.gnrbaseclasses import BaseComponent

class Service(RemoteService):

    def __init__(self,parent,**kwargs):
        self.parent = parent
        self.wsk = parent.wsk
        self.service_tbl = self.parent.db.table('sys.service')

    @property
    def service_identifier(self):
        if not hasattr(self,'_service_identifier'):
            service_record = self.service_tbl.record(implementation='remotewsservice',
                                                            service_name=self.service_name,ignoreMissing=True).output('dict')
            self._service_identifier = service_record['service_identifier']
        return self._service_identifier

    def linked_services(self):
        query_kwargs={'websocket_service':self.service_identifier}
        return self.parent.db.table('sys.service').query('$service_type,$service_name',
            where="""CAST( (xpath('/GenRoBag/websocket_service/text()', CAST($parameters as XML) ) )[1]  AS text) =:websocket_service""", **query_kwargs).fetch()

    def send_message(self, command, data=None, **kwargs):
        self.wsk.sendCommandToRemoteService(self.service_name,command=command,data=data)

    def on_message(self, topic=None,target_service=None,**kwargs):
        if target_service:
            service_type, service_name = target_service.split('.')
            linked_services  = [target_service.split('.')]
        else:
            linked_services  = [(s['service_type'],s['service_name']) for s in self.linked_services()]
        for service_name, service_type in linked_services:
            service = self.parent.getService(service_type,service_name)
            handler = getattr(service,f'on_{topic}',None)
            if handler:
                handler(**kwargs)



class ServiceParameters(BaseComponent):
    def service_parameters(self,pane,datapath=None,**kwargs):
        bc = pane.borderContainer()
        fb = bc.contentPane(region='top').formbuilder(datapath=datapath)
        
