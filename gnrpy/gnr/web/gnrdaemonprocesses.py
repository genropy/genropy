#!/usr/bin/env python
# encoding: utf-8
#

from datetime import datetime
from multiprocessing import Process, get_logger, cpu_count
import threading
import os
import time

class GnrDaemonServiceManager(object):
    def __init__(self, parent=None, sitename = None, monitor_interval=None):
        self.parent = parent
        self.sitename = sitename
        self.multiprocessing_manager = self.parent.multiprocessing_manager
        self.services = dict()
        self.services_info = dict()
        self.services_monitor = dict()
        self.monitor_interval = monitor_interval or 10


    @property
    def site(self):
        if not hasattr(self, '_site'):
            from gnr.web.gnrwsgisite import GnrWsgiSite
            self._site = GnrWsgiSite(self.sitename, noclean=True)
        return self._site

    def terminate(self):
        self.monitor_running=False
        for p in list(self.services.values()):
            if p and p.is_alive():
                p.terminate()

    def is_alive(self):
        for p in list(self.services.values()):
            if p and p.is_alive():
                return True
        return False

    def reloadServices(self, service_identifier=None):
        def needReload(service):
            service_info = self.services_info.get(service['service_identifier']) or dict()
            if service['__mod_ts']!=service_info.get('__mod_ts'):
                return True
            return False
        where = '$daemon IS TRUE'
        if service_identifier:
            service_identifier = service_identifier.split(',')
            where = '%s AND $service_identifier =:service_identifier'%where
        service_tbl = self.site.db.table('sys.service')
        services = service_tbl.query('$service_identifier,$service_type,$service_name,$__mod_ts,$disabled',
            where=where).fetch()
        old_services = list(self.services_info.keys()) or service_identifier or []
        old_services = dict([(o,True) for o in old_services])
        for service in services:
            service_identifier = service['service_identifier']
            old_services.pop(service_identifier, None)
            if needReload(service):
                self.services_info[service_identifier] = dict(service)
                self.updateService(service_identifier)
        for service_identifier in old_services:
            self.services_info.pop(service_identifier, None)
            self.updateService(service_identifier)

    def updateService(self, service_identifier):
        process = self.services.get(service_identifier)
        if process and process.is_alive():
            self.stopService(service_identifier)



    def start(self):
        #time.sleep(1)

        #self.reloadServices()
        self.monitor_running = True
        monitor_thread = threading.Thread(target=self.monitorServices)
        monitor_thread.setDaemon(True)
        monitor_thread.start()

    def stopService(self, service_identifier):
        stop_thread = threading.Thread(target=self._stopService, args=(service_identifier,))
        stop_thread.setDaemon(True)
        stop_thread.start()

    def _stopService(self, service_identifier):
        process = self.services.get(service_identifier)
        if process and process.is_alive():
            running = self.services_monitor.get(service_identifier)
            if running:
                running.value = False
            process.join(30)
            if process.is_alive():
                process.terminate()

    def startService(self, service_identifier):
        service = self.services_info.get(service_identifier)
        if not service:
            return
        service_type = service['service_type']
        service_name = service['service_name']
        _running = self.services_monitor.setdefault(service_identifier, self.multiprocessing_manager.Value('b',True))
        _running.value = True
        process = Process(name='svc_%s_%s' %(self.sitename, service_identifier),
                    target=self.runService, args=(service_type, service_name, _running))
        process.daemon = True
        process.start()
        return process

    def runService(self, service_type, service_name, _running,**kwargs):
        service = GnrDaemonService(site=self.site,service_type=service_type,service_name=service_name,
            _running=_running,**kwargs)
        # potrei anche fare direttamente qui il server senza wrapper, vedere
        time.sleep(1)
        service.start()

    def monitorServices(self):
        counter = 0
        while self.monitor_running:
            time.sleep(1)
            counter +=1
            if counter%self.monitor_interval:
                continue
            self.reloadServices()
            counter = 0
            for service_identifier, service in list(self.services_info.items()):
                process = self.services.get(service_identifier)
                if service['disabled']:
                    continue
                if not process or not process.is_alive():
                    process = self.startService(service_identifier)
                    self.services[service_identifier] = process

class GnrDaemonService(object):
    def __init__(self, site=None, service_type=None, service_name=None, _running=None,**kwargs):
        self.site = site
        self.service = self.site.getService(service_type,service_name)
        self._running = _running

    def start(self):
        if hasattr(self.service,'run'):
            self.service.run(running=self._running)
        

