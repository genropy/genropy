#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  data retention manager
#
#  Copyright (c) 2025 Softwell. 
#

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    css_requires = 'public'
    py_requires = 'gnrcomponents/framegrid:FrameGrid'
    auth_main = 'superadmin,_DEV_'

    def windowTitle(self):
        return '!!Data retention policies'

    def main(self, root, **kwargs):
        bc = root.borderContainer(datapath='main')
        top = bc.borderContainer(region='top', height='250px')
        self.policyFrame(top.contentPane(region='center'))
        
    def policyStruct(self, struct):
        r = struct.view().rows()
        r.cell('table_fullname', width='10em', name='Table')
        r.cell('filter_column', width='10em', name='Filter Column')
        r.cell('retention_period_default', name='Retention (days)', width='5em')
        r.cell('retention_period_custom', dtype="L",
               name='Custom Retention (days)', width='10em',
               edit=True)

    def policyFrame(self, pane):
        frame = pane.bagGrid(frameCode='policies', datapath='policies',
                             storepath='policies.store',
                             struct=self.policyStruct, _class='pbl_roundedGroup',
                             margin='2px')
        
        #frame.grid.bagStore(storepath='policies.store', storeType='ValuesBagRows')

        bar = frame.top.slotBar('2,vtitle,*,save_policies,2',
                                vtitle='Policies',_class='pbl_roundedGroupLabel')
        
        bar.save_policies.slotButton('!!Save policies').dataRpc(
            self.save_policies,
            policies='=policies.store'
        )
        
        pane.dataRpc(
            'policies.store',
            self.get_policies,
            _onStart=True,
        )
        


    @public_method
    def save_policies(self, policies=None):
        '''
        Save the new policies. If the value is changed from the default, either
        insert or update an existing customization record. If the value is the same,
        just delete the database record
        '''
        self.db.application.saveRetentionPolicy(policies)
        
    @public_method
    def get_policies(self):
        '''
        Get currently policy configuration, loaded from the default
        configuration merged with overrides defined on the database
        '''
        result_data = Bag()
        policies = self.db.application.retentionPolicy
        if policies:
            for i, (k, v) in enumerate(policies.items()):
                r = dict(
                    table_fullname=k,
                    **v
                    )
                result_data.setItem(f'r_{i:03}', Bag(r))
        return Bag(result_data)

