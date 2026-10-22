# -*- coding: utf-8 -*-

# thpage.py
# Created by Francesco Porcari on 2011-05-05.
# Copyright (c) 2011 Softwell. All rights reserved.



class GnrCustomWebPage(object):
    js_requires = 'helpeditor'
    
    def windowTitle(self):
        return f"""{self.db.table(self.maintable).attributes.get('name_plural') or self.db.table(self.maintable).attributes.get('name_long')} helper"""


    @classmethod
    def getMainPackage(cls,request_args=None,request_kwargs=None):
        return request_kwargs.get('th_from_package') or request_args[0]
     
    @property
    def maintable(self):
        callArgs = self.getCallArgs('th_pkg','th_table','th_pkey')
        return '%(th_pkg)s.%(th_table)s' %callArgs



    @property
    def pagename(self):
        callArgs = self.getCallArgs('th_pkg','th_table','th_pkey')  
        return 'helper_%(th_pkg)s_%(th_table)s' %callArgs

    #FOR ALTERNATE MAIN HOOKS LOOK AT public:TableHandlerMain component
    def main(self,root,**kwargs):
        helperPath=self.packageResourcePath(self.maintable,'helper.xml')
        form = root.frameForm(frameCode='helper',store_startKey=helperPath,
                              datapath='main',store=True,**kwargs)
        form.store.handler('load',handler_type='document')
        form.store.handler('save',handler_type='document')

        box = form.record.div(datapath='.wdg_help')
        form.dataController("""
                    data.forEach(function(n){
                                console.log('n',n);
                                //let cell = box._('div',{lbl:n.label,border:'1px solid silver',height:'40px',margin:'2px'});
                                box._('textbox',{value:`^.${n.label}`,lbl:n.label})
                            });
                    """,box=box,
                        data='=#FORM.record.wdg_help',
                        _fired='^#FORM.controller.loaded')
        form.bottom.slotButton('Save',action='this.form.save()')