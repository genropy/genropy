#!/usr/bin/python
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('title')
        r.fieldcell('letterhead_id')
        r.fieldcell('tag_rule', width='20em')
        r.fieldcell('group_code', width='10em')

    def th_order(self):
        return 'title'

    def th_query(self):
        return dict(column='title', op='contains', val='')



class Form(BaseComponent):

    def th_form(self, form):
        bc = form.center.borderContainer()
        top = bc.borderContainer(region='top',datapath='.record', height='120px')
        
        fb = top.contentPane(region='center').formbuilder(cols=2, border_spacing='4px', fld_width='100%')
        fb.field('title', colspan=2)
        fb.field('tag_rule', tag='checkboxtext', table='adm.htag', popup=True, cols=4, colspan=2)
        fb.field('group_code', tag='checkboxtext', table='adm.group', popup=True, cols=4, colspan=2)
        fb.field('confirm_label',width='20em')
        fb.field('letterhead_id')
        
        self.linkedQueryPane(top.roundedGroup(region='right',width='400px', 
                                title='!![en]Restriction query'))
        
        sc = bc.stackContainer(region='center')
        self.templatePage(sc.framePane(title='!!Template'))
        self.connectedUser(sc.contentPane(title='!!Users'))

    def templatePage(self,frame):
        centerpane = frame.center.contentPane(overflow='auto')
        centerpane.dataRecord('#FORM.sample_letterhead','adm.htmltemplate',pkey='^#FORM.record.letterhead_id',
                                _if='pkey',_else='return new gnr.GnrBag();')

        centerpane.dataFormula('#FORM.available_height','(center_height || 297)+"mm";',center_height='^#FORM.sample_letterhead.center_height')
        centerpane.dataFormula('#FORM.available_width','(center_width || 210)+"mm";',center_width='^#FORM.sample_letterhead.center_width')
        paper = centerpane.div(height='^#FORM.available_height',width='^#FORM.available_width',margin='10px',border='1px dotted silver')
        bar = frame.top.slotToolbar('5,parentStackButtons,*,selector,5')
        fb = bar.selector.formbuilder(cols=1, border_spacing='0')

        fb.dbSelect(dbtable='adm.user',value='^#FORM.testuser.pkey',lbl='Test User',#condition='$tipo_id=:t_id',
                    condition_t_id='^#FORM.pkey')
        rpc = fb.dataRecord('#FORM.testuser.record','adm.user',
                            pkey='==_pkey || "*newrecord*"',
                            _pkey='^#FORM.testuser.pkey',
                            ignoreMissing=True)

        paper.templateChunk(template='^#FORM.record.template',table='adm.user',editable=True,dataProvider=rpc,
                            datasource='^#FORM.testuser.record',
                            showLetterhead='^#FORM.sample_letterhead.id',
                            constrain_height='^#FORM.available_height',
                            constrain_width='^#FORM.available_width',
                            constrain_border='1px solid silver',
                            constrain_shadow='3px 3px 5px gray',
                            constrain_margin='4px',
                            constrain_rounded=3,
                            selfsubscribe_onChunkEdit='this.form.save();')
        
    @public_method
    def getSampleLetterhead(self,letterhead_id=None):
        pass
    
    def linkedQueryPane(self,pane):
        dlg=self.linkedQueryDialog(pane,datapath='#FORM.linked_query_editor')
        pane.lightButton('^#FORM.record.notif_linked_query_desc',
                        action="""
                        if(query){
                            dlgNode.setRelativeData('.store',query.deepCopy());
                        }
                        dlgNode.widget.show();
                        let querypane = genro.nodeById('notification_query_pane_root');
                        querypane.querymanager = new gnr.FakeTableHandler(querypane,table);
                        querypane.querymanager.createQueryPane();
                        """, dlgNode=dlg, query='=#FORM.record.linked_query', 
                        table='adm.user', padding='10px')
        dlg.dataRpc('#FORM.record.notif_linked_query_desc',
                        self.getQueryCaption,
                        query='=#FORM.record.linked_query',
                        _fired='^.reload_query_desc')

    def linkedQueryDialog(self,pane,querypath=None,datapath=None):
        dlg = pane.dialog(title='!![en]Linked query',closable=True,datapath=datapath)
        frame = dlg.framePane(frameCode='notification_linked_query',height='400px',width='500px')
        frame.center.contentPane(datapath='.store').div(nodeId='notification_query_pane_root')
        footer = frame.bottom.slotBar('*,confirm,5',border='1px solid silver',height='23px')
        footer.confirm.button(label='!!Confirm',action="""
                            let newdata = store.deepCopy();
                            SET #FORM.record.linked_query = newdata;
                            dlgNode.widget.hide();
                            this.form.save({always:true});
                            """,store='=.store',dlgNode=dlg)
        return dlg

    @public_method
    def getQueryCaption(self,query=None,**kwargs):
        return self.db.whereTranslator.toHtml(self.db.table('adm.user'),query)
    
    def connectedUser(self,pane):
        th = pane.plainTableHandler(relation='@notification_users',viewResource='ViewFromNotification',delrow=True,picker='user_id')
        th.view.top.bar.replaceSlots('vtitle','parentStackButtons')

    @public_method
    def th_onLoading(self, record, newrecord, loadingParameters, recInfo):
        if record['linked_query']:
            record['notif_linked_query_desc'] = self.db.whereTranslator.toHtml(self.db.table('adm.user'),record['linked_query'])
        else:
            record['notif_linked_query_desc'] = '!!Add linked query'
            
    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px', duplicate=True)


class FormEmbed(Form):
    def th_form(self, form):
        bc = form.center.borderContainer()
        left = bc.borderContainer(region='left', width='400px', datapath='.record')
        fb = left.roundedGroup(title='!![en]Notification parameters', region='top', 
                               height='50%').formbuilder(cols=1)
        fb.field('title')
        fb.field('tag_rule', tag='checkboxtext', table='adm.htag', popup=True, cols=4)
        fb.field('group_code', tag='checkboxtext', table='adm.group', popup=True, cols=4)
        fb.field('confirm_label',width='20em')
        fb.field('letterhead_id')
        
        self.linkedQueryPane(left.roundedGroup(region='center', title='!![en]Restriction query'))

        sc = bc.stackContainer(region='center')
        self.templatePage(sc.framePane(title='!!Template'))
        self.connectedUser(sc.contentPane(title='!!Users'))
        
    def th_options(self):
        return dict(showtoolbar=False, autoSave=True)