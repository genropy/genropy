#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  task monitoring
#
#  Copyright (c) 2025 Softwell. 
#

import json
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

        center = bc.borderContainer(region='center')
        self.pendingfailedFrame(center.contentPane(region='center'))

        bottom = bc.borderContainer(region='bottom', height='250px')
        self.statusFrame(bottom.contentPane(region='center'))

    def _get_status_data(self):
        if (time.time() - self._status_cache_ts) > 5:
            self._status_cache = requests.get(f"{GNR_SCHEDULER_URL}/status").json()
            self._status_cache_ts = time.time()
        return self._status_cache
        
    # WORKERS
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


    # PENDING/FAILED
    
    def pendingfailedStruct(self, struct):
        r = struct.view().rows()
        r.cell('status', width='10em', name='Status')
        r.cell('task_id', name='Task ID', width='15em')
        r.cell('task_name', name='Task Name', width='15em')
        r.cell('command', name='Command', width='15em')
        r.cell('last_scheduled_ts', name='Last Scheduled', width='15em')
        r.cell('table_name', name='Table name', width='15em')
        r.cell('run_id', name='Run ID', width='30em')

    def pendingfailedFrame(self,pane):
        frame = pane.frameGrid(frameCode='pendingfailedStatus', datapath='pendingfailedStatus',
                               struct=self.pendingfailedStruct, _class='pbl_roundedGroup',
                               margin='2px')
        frame.grid.bagStore(storepath='pendingfailedStatus.store', storeType='AttributesBagRows',
                            sortedBy='=.grid.sorted',
                            data='^pendingfailedStatus.loaded_data', selfUpdate=True)
        
        pane.dataRpc('pendingfailedStatus.loaded_data',
                     self.pendingfailedStatus,
                     _onStart=True,
                     _timing=self.REFRESH_INTERVAL)
        frame.top.slotBar('2,vtitle,*',vtitle='Pending / Failed tasks',_class='pbl_roundedGroupLabel')

    @public_method
    def pendingfailedStatus(self):
        '''
        prepare data for pending/failed tasks obtained
        from the scheduler status API endpoint
        '''
        result = Bag()
        failed_show_keys = ['task_name',
                     'command', 'last_scheduled_ts',
                     'table_name']
        try:
            status = self._get_status_data()
            # PENDING
            for i, (k, v) in enumerate(status.get("pending", {}).items()):
                desc = dict(v[0])
                payload = {x[0]:x[1] for x in json.loads(desc['payload'])}
                for k in failed_show_keys:
                    desc[k] = payload[k]
                desc['status'] = "Pending"
                desc['last_scheduled_ts'] = v[1]
                result.setItem(i, None, **desc)

            # FAILED
            for i, v in enumerate(status.get("failed", [])):
                payload = {x[0]:x[1] for x in json.loads(v['payload'])}
                for k in failed_show_keys:
                    v[k] = payload[k]
                
                v['status'] = "Failed"
                result.setItem(i, None, **v)
        except:
            raise
            self.clientPublish('floating_message', message="Can't connect to scheduler process", messageType='error')
            
        return result


    # SCHEDULER STATUS
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
        
