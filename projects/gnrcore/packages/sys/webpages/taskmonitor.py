#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  task monitoring
#
#  Copyright (c) 2025 Softwell. 
#

import time
import datetime
import requests

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag
from gnr.web.gnrtask import GNR_SCHEDULER_URL


class GnrCustomWebPage(object):
    css_requires='public'
    py_requires='gnrcomponents/framegrid:FrameGrid'
    auth_main = 'superadmin,_DEV_'

    CACHE_AGE_SECONDS = 4
    REFRESH_INTERVAL = CACHE_AGE_SECONDS*2
    _status_cache_ts = time.time()-CACHE_AGE_SECONDS
    _status_cache = {"workers":{}, "workers_total": 0,
                     "total_tasks": 0, "queue_size": 0,
                     "pending": {}, "failed": {}}

    
    def windowTitle(self):
        return '!!Task Monitor'

    def main(self, root, **kwargs):
        
        bc = root.borderContainer(datapath='main')

        top = bc.borderContainer(region='top', height='250px')
        self.workersFrame(top.contentPane(region='center'))

        bottom = bc.borderContainer(region='center', height='250px')
        self.statusFrame(bottom.contentPane(region='center'))
        
    def workersStruct(self, struct):
        r = struct.view().rows()
        r.cell('hostname', width='10em', name='Hostname')
        r.cell('pid', name='Pid', width='5em')
        r.cell('worked_tasks', name='Worked tasks', width='10em')
        r.cell('seen_ts', width='20em',
               name='Last seen', dtype='DHZ')

    def workersFrame(self,pane):
        frame = pane.frameGrid(frameCode='runningWorkers', datapath='runningWorkers',
                               struct=self.workersStruct, _class='pbl_roundedGroup',
                               margin='2px')
        frame.grid.bagStore(storepath='runningWorkers.store', storeType='AttributesBagRows',
                            sortedBy='=.grid.sorted',
                            data='^runningWorkers.loaded_data', selfUpdate=True)
        
        pane.dataRpc('runningWorkers.loaded_data',
                     self.runningWorkers,
                     _onStart=True,
                     _timing=self.REFRESH_INTERVAL)
        frame.top.slotBar('2,vtitle,*',vtitle='Running workers',_class='pbl_roundedGroupLabel')

    def _get_status_data(self):
        if (time.time() - self._status_cache_ts) > 5:
            self._status_cache = requests.get(f"{GNR_SCHEDULER_URL}/status").json()
            self._status_cache_ts = time.time()
        return self._status_cache
        
    @public_method
    def runningWorkers(self):

        result = Bag()
        try:
            status = self._get_status_data()
            for i, (k, v) in enumerate(status.get('workers', {}).items()):
                v = dict(v)
                _, v['hostname'], v['pid'] = k.split('-')
                v['seen_ts'] = v['lastseen']
                result.setItem(i, None, **v)
        except:
            self.clientPublish('floating_message', message="Can't connect to scheduler process", messageType='error')
            
        return result

    def statusStruct(self, struct):
        r = struct.view().rows()
        r.cell('key', width='15em', name='Attribute')
        r.cell('value', name='Value', width='40em')
        
    def statusFrame(self,pane):
        frame = pane.frameGrid(frameCode='schedulerStatus', datapath='schedulerStatus',
                               struct=self.statusStruct,
                               _class='pbl_roundedGroup',
                               margin='2px')
        frame.grid.bagStore(storepath='schedulerStatus.store', storeType='AttributesBagRows',
                            sortedBy='=.grid.sorted',
                            data='^schedulerStatus.loaded_data', selfUpdate=True)
        
        pane.dataRpc('schedulerStatus.loaded_data',self.schedulerStatus,
                     _onStart=True,
                     _timing=self.REFRESH_INTERVAL)

        frame.top.slotBar('2,vtitle,*',vtitle='Scheduler status',_class='pbl_roundedGroupLabel')

    @public_method
    def schedulerStatus(self):
        result = Bag()
        try:
            status = self._get_status_data()
            result.setItem("Total workers", None, dict(key="Total workers",
                                                       value=status['workers_total']))
            result.setItem("Total tasks", None, dict(key="Total tasks",
                                                     value=status['total_tasks']))
            result.setItem("Queue size", None, dict(key="Queue size",
                                                    value=status['queue_size']))
            result.setItem("Total pending tasks", None, dict(key="Total pending tasks",
                                                             value=len(status['pending'])))
            result.setItem("Total failed tasks", None, dict(key="Total failed tasks",
                                                            value=len(status['failed'])))
            result.setItem("Last status update", None, dict(key="Last status update",
                                                            value=str(datetime.datetime.fromtimestamp(self._status_cache_ts))))
        except:
            self.clientPublish('floating_message', message="Can't connect to scheduler process", messageType='error')
        return result
        
