#!/usr/bin/python
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method

class View(BaseComponent):
    def th_hiddencolumns(self):
        return '$service_identifier'


    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('service_name')
        r.fieldcell('service_type')
        r.fieldcell('implementation')
        #r.fieldcell('extrainfo',width='30em')

    def th_order(self):
        return 'service_identifier'

    def th_query(self):
        return dict(column='service_identifier', op='contains', val='')

class Form(BaseComponent):

    def th_form(self, form):
        bc = form.center.borderContainer(datapath='.record')
        fb = bc.contentPane(region='top').formbuilder(cols=2, border_spacing='4px')
        fb.field('service_type',disabled=True)
        fb.field('implementation',disabled=True)
        fb.field('service_name',colspan=2,validate_notnull=True,width='100%',disabled=True)
        #fb.field('daemon',colspan=1,html_label=True)
        fb.field('disabled',colspan=1,html_label=True)

        center = bc.contentPane(region='center')
        center.contentPane().remote(self.buildServiceParameters,service_type='=.service_type',
                                                    implementation='=.implementation',
                                                    service_name='=.service_name', 
                                                    _if="service_type && implementation",
                                                    _fired='^#FORM.controller.loaded',
                                                    _async=True,_waitingMessage=True)


    @public_method
    def buildServiceParameters(self,pane,service_type=None,implementation=None,service_name=None,**kwargs):
        mixinpath = '/'.join(['services',service_type,implementation])
        self.mixinComponent('%s:ServiceParameters' %mixinpath,safeMode=True)
        if hasattr(self,'service_parameters'):
            self.service_parameters(pane,datapath='.parameters', service_name=service_name,
                                    service_type=service_type, implementation=implementation)

    def th_options(self):
        return dict(defaultPrompt=dict(title='!!New service',
                                    fields=[dict(value='^.service_type',lbl='!!Service type', 
                                                 hasDownArrow=True,
                                                 tag='remoteSelect', 
                                                 method='_table.sys.service.getAvailableServiceTree',
                                                 auxColumns='service_type,implementation', 
                                                 validate_notnull=True,
                                                 selected_implementation='.implementation'),
                                            dict(value='^.service_name',lbl='!!Service name',
                                                 validate_regex='![^A-Za-z0-9_]', 
                                                 validate_notnull=True,
                                                 validate_regex_error='!!Invalid code: Only letters and numbers are allowed')],doSave=True))