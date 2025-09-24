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
                     "total_tasks": 0, "total_queue_size": 0,
                     "pending": {}, "failed": {}}

    
    def windowTitle(self):
        return '!!Task Monitor'

    def main(self, root, **kwargs):
        
        bc = root.borderContainer(datapath='main')

        top = bc.borderContainer(region='top', height='250px')
        self.statusFrame(top.contentPane(region='left', width="50%"))
        self.queuesizeFrame(top.contentPane(region='right', width="50%"))

        center = bc.borderContainer(region='center')
        self.pendingfailedFrame(center.contentPane(region='center'))

        bottom = bc.borderContainer(region='bottom', height='250px')
        self.workersFrame(bottom.contentPane(region='center'))
        
    def _get_status_data(self):
        try:
            if (time.time() - self._status_cache_ts) > self.CACHE_AGE_SECONDS:
                self._status_cache = requests.get(f"{GNR_SCHEDULER_URL}/status").json()
                self._status_cache_ts = time.time()
            return self._status_cache, None
        except:
            return None, "Can't connect to scheduler process"

    # WORKERS
    def workersStruct(self, struct):
        r = struct.view().rows()
        r.cell('hostname', width='10em', name='Hostname')
        r.cell('queue_name', width='10em', name='Queue')
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
        
        pane.dataFormula(".workers_refresh_timer", "dflt",
                         _onStart=True,
                         dflt=self.REFRESH_INTERVAL,
                         _fire_reset='^.workers_refresh_reset')

        pane.dataController(
            """
            if(result.getItem('error')) {
              genro.publish("floating_message",
                {message: result.getItem('error'), messageType:'error'}
              );
              SET .workers_refresh_timer = current*2
            } else {
              FIRE .workers_refresh_reset;
              SET runningWorkers.loaded_data =result.getItem('data');
            }
            """,
            current='=.workers_refresh_timer',
            result='^.workers_result')
        
        pane.dataRpc(
            self.runningWorkers,
            _onStart=True,
            _onResult="""
            FIRE .workers_result =result;
            """,
            _timing='^.workers_refresh_timer'
        )
        
        frame.top.slotBar('2,vtitle,*',vtitle='Running workers',_class='pbl_roundedGroupLabel')
 
    @public_method
    def runningWorkers(self):
        result_data = Bag()
        status, error = self._get_status_data()
        if status:
            for i, (k, v) in enumerate(status.get('workers', {}).items()):
                v = dict(v)
                _, v['hostname'], v['pid'] = k.split('-')
                v['seen_ts'] = v['lastseen']
                result_data.setItem(i, None, **v)
        return Bag(data=result_data, error=error)

    # QUEUE STATUS

    def queuesizeStruct(self, struct):
        r = struct.view().rows()
        r.cell('queue_name', width='20em', name='Queue')
        r.cell('counter', width='20em', name='Total tasks')
        
    def queuesizeFrame(self, pane):
        frame = pane.frameGrid(frameCode='queuesizeStatus', datapath='queuesizeStatus',
                               struct=self.queuesizeStruct, _class='pbl_roundedGroup',
                               margin='2px')
        frame.grid.bagStore(storepath='queuesizeStatus.store', storeType='AttributesBagRows',
                            sortedBy='=.grid.sorted',
                            data='^queuesizeStatus.loaded_data', selfUpdate=True)

        pane.dataFormula(".queuesize_refresh_timer", "dflt",
                         _onStart=True,
                         dflt=self.REFRESH_INTERVAL,
                         _fire_reset='^.queuesize_refresh_reset')
        
        pane.dataController(
            """
            if(result.getItem('error')) {
              genro.publish("floating_message",
                            {message:result.getItem('error'),
                             messageType:'error'}
             );
              SET .queuesize_refresh_timer = current*2;
            } else {
              FIRE .queuesize_refresh_reset;
              SET queuesizeStatus.loaded_data =result.getItem('data');
            }
            """,
            current='=.queuesize_refresh_timer',
            result='^.queuesize_result')

        pane.dataRpc(self.queuesizeStatus,
                     _onStart=True,
                     _onResult='FIRE .queuesize_result =result;',
                     _timing='^.queuesize_refresh_timer')
        frame.top.slotBar('2,vtitle,*',vtitle='Queues',_class='pbl_roundedGroupLabel')

    @public_method
    def queuesizeStatus(self):
        '''
        prepare data for enqueued tasks obtained
        from the scheduler status API endpoint
        '''
        result = Bag()
        status,error = self._get_status_data()
        if status:
            for i, (k, v) in enumerate(status.get("queues_sizes", {}).items()):
                desc = dict(queue_name=k,
                            counter=v)
                result.setItem(i, None, **desc)
        return Bag(data=result,error=error)
    
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

    def pendingfailedFrame(self, pane):
        frame = pane.frameGrid(frameCode='pendingfailedStatus', datapath='pendingfailedStatus',
                               struct=self.pendingfailedStruct, _class='pbl_roundedGroup',
                               margin='2px')
        frame.grid.bagStore(storepath='pendingfailedStatus.store', storeType='AttributesBagRows',
                            sortedBy='=.grid.sorted',
                            data='^pendingfailedStatus.loaded_data', selfUpdate=True)

        pane.dataFormula(".pendingfailed_refresh_timer", "dflt",
                         _onStart=True,
                         dflt=self.REFRESH_INTERVAL,
                         _fire_reset='^.pendingfailed_refresh_reset')
        
        pane.dataController(
            """
            if(result.getItem('error')) {
              genro.publish("floating_message",
                            {message:result.getItem('error'),
                             messageType:'error'}
             );
              SET .pendingfailed_refresh_timer = current*2;
            } else {
              FIRE .pendingfailed_refresh_reset;
              SET pendingfailedStatus.loaded_data =result.getItem('data');
            }
            """,
            current='=.pendingfailed_refresh_timer',
            result='^.pendingfailed_result')

        pane.dataRpc(self.pendingfailedStatus,
                     _onStart=True,
                     _onResult='FIRE .pendingfailed_result =result;',
                     _timing='^.pendingfailed_refresh_timer')
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
        status,error = self._get_status_data()
        if status:
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
            
        return Bag(data=result,error=error)


    # SCHEDULER STATUS
    def statusStruct(self, struct):
        r = struct.view().rows()
        r.cell('key', name='Attribute', width='auto')
        r.cell('value', name='Value', width='auto')
        
    def statusFrame(self,pane):
        frame = pane.frameGrid(frameCode='schedulerStatus', datapath='schedulerStatus',
                               struct=self.statusStruct,
                               _class='pbl_roundedGroup',
                               margin='2px')
        frame.grid.bagStore(storepath='schedulerStatus.store', storeType='AttributesBagRows',
                            sortedBy='=.grid.sorted',
                            data='^schedulerStatus.loaded_data', selfUpdate=True)
        pane.dataFormula('.schedulerStatus_refresh_timer', 'dflt',
                         _onStart=True,
                         dflt=self.REFRESH_INTERVAL,
                         _fire_reset='^.schedulerStatus_refresh_reset')
        pane.dataController(
            """
            if(result.getItem('error')) {
              genro.publish("floating_message",
                {message: result.getItem('error'), messageType:'error'}
              );
              SET .schedulerStatus_refresh_timer = current*2
            } else {
              FIRE .schedulerStatus_refresh_reset;
              SET schedulerStatus.loaded_data =result.getItem('data');
            }

            """,
            current='=.schedulerStatus_refresh_timer',
            result='^.schedulerStatus_result')
        
        pane.dataRpc(
            self.schedulerStatus,
            _onStart=True,
            _onResult="FIRE .schedulerStatus_result =result",
            _timing='^.schedulerStatus_refresh_timer')

        frame.top.slotBar('2,vtitle,*',vtitle='Scheduler status',_class='pbl_roundedGroupLabel')

    @public_method
    def schedulerStatus(self):
        result = Bag()
        status,error = self._get_status_data()
        if status:
            result.setItem("Scheduler startup", None, dict(key="Scheduler startup",
                                                       value=status['startup_time']))
            result.setItem("Scheduler current time", None, dict(key="Scheduler current time",
                                                       value=status['scheduler_current_time']))
            result.setItem("Total workers", None, dict(key="Total workers",
                                                       value=status['workers_total']))
            result.setItem("Total tasks", None, dict(key="Total tasks",
                                                     value=status['total_tasks']))
            result.setItem("Total Queue size", None, dict(key="Total Queue size",
                                                    value=status['total_queue_size']))
            result.setItem("Total pending tasks", None, dict(key="Total pending tasks",
                                                             value=len(status['pending'])))
            result.setItem("Total failed tasks", None, dict(key="Total failed tasks",
                                                            value=len(status['failed'])))
            result.setItem("Last status update", None, dict(key="Last status update",
                                                            value=str(datetime.datetime.fromtimestamp(self._status_cache_ts))))
        return Bag(data=result,error=error)
        
