#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  task monitoring
#
#  Copyright (c) 2025 Softwell. 
#
import datetime
import requests

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag
from gnr.web.gnrtask import GNR_SCHEDULER_URL

class GnrCustomWebPage(object):
    css_requires='public'
    py_requires='gnrcomponents/framegrid:FrameGrid'
    auth_main = 'superadmin,_DEV_'

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
        r.cell('hostname', width='10em',name='Hostname')
        r.cell('pid',name='Pid',width='5em')
        r.cell('seen_ts',width='20em',name='Last seen',dtype='DH')

    def workersFrame(self,pane):
        frame = pane.frameGrid(frameCode='runningWorkers', datapath='runningWorkers',
                               struct=self.workersStruct, _class='pbl_roundedGroup',
                               margin='2px')
        frame.grid.bagStore(storepath='runningWorkers.store', storeType='AttributesBagRows',
                            sortedBy='=.grid.sorted',
                            data='^runningWorkers.loaded_data', selfUpdate=True)
        pane.dataRpc('runningWorkers.loaded_data',self.runningWorkers, _onStart=True, _timing=5)
        frame.top.slotBar('2,vtitle,*',vtitle='Running workers',_class='pbl_roundedGroupLabel')

    @public_method
    def runningWorkers(self):
        result = Bag()
        status = requests.get(f"{GNR_SCHEDULER_URL}/status").json()
        for i, (k, v) in enumerate(status['workers'].items()):
            v = dict(v)
            _, v['hostname'], v['pid'] = k.split('-')
            v['seen_ts'] = v['lastseen']
            result.setItem(i, None, **v)
        return result

    def statusStruct(self, struct):
        r = struct.view().rows()
        r.cell('key', width='15em',name='Attribute')
        r.cell('value',name='Value',width='40em')
        
    def statusFrame(self,pane):
        frame = pane.frameGrid(frameCode='schedulerStatus', datapath='schedulerStatus',
                               struct=self.statusStruct,
                               _class='pbl_roundedGroup',
                               margin='2px')
        frame.grid.bagStore(storepath='schedulerStatus.store', storeType='AttributesBagRows',
                            sortedBy='=.grid.sorted',
                            data='^schedulerStatus.loaded_data', selfUpdate=True)
        pane.dataRpc('schedulerStatus.loaded_data',self.schedulerStatus, _onStart=True, _timing=5)

        frame.top.slotBar('2,vtitle,*',vtitle='Scheduler status',_class='pbl_roundedGroupLabel')

    @public_method
    def schedulerStatus(self):
        result = Bag()
        status = requests.get(f"{GNR_SCHEDULER_URL}/status").json()
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
                                                   value=str(datetime.datetime.utcnow())))

        return result
        
