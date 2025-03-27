#!/usr/bin/python
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import metadata, customizable

class View(BaseComponent):

    def th_groupedStruct(self,struct):
        "Account View"
        r = struct.view().rows()
        r.fieldcell('@account_id.account_name', name='!!Account', width='20em')
        r.cell('_grp_count', name='Cnt', width='4em', group_aggr='sum')
    
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('subject',width='auto')
        r.fieldcell('to_address',width='18em')
        r.fieldcell('cc_address',width='18em')
        r.fieldcell('bcc_address',width='18em')
        r.fieldcell('uid',width='7em')
        r.fieldcell('__ins_ts',width='7em')
        #r.fieldcell('user_id',width='35em')
        r.fieldcell('account_id',width='12em')

    def th_queryBySample(self):
        return dict(fields=[dict(field='send_date',lbl='!!Send date',width='7em'),
                            dict(field='subject', lbl='!!Subject'),
                            dict(field='body_plain',lbl='!!Content'),
                            dict(field='to_address', lbl='!!To address'),
                            dict(field='from_address', lbl='!!From address')],cols=5,isDefault=True)

    def th_order(self):
        return '__ins_ts:d'

    def th_query(self):
        return dict(column='subject',op='contains', val='',runOnStart=False)

    def th_top_upperbar(self,top):
        top.slotToolbar('5,sections@in_out,*,sections@sendingstatus',
                        childname='upper',_position='<bar')

    def th_struct_sending_error(self,struct):
        r = struct.view().rows()
        r.fieldcell('subject',width='auto')
        r.fieldcell('to_address',width='18em')
        r.fieldcell('cc_address',width='18em')
        r.fieldcell('bcc_address',width='18em')
        r.fieldcell('error_msg',width='10em')
        r.fieldcell('error_ts',width='8em')
        r.fieldcell('__ins_ts',width='7em')
        r.fieldcell('account_id',width='12em')

    def th_struct_sent(self,struct):
        r = struct.view().rows()
        r.fieldcell('subject',width='auto')
        r.fieldcell('to_address',width='18em')
        r.fieldcell('cc_address',width='18em')
        r.fieldcell('bcc_address',width='18em')
        r.fieldcell('__ins_ts',width='7em')        
        r.fieldcell('send_date',width='8em')
        r.fieldcell('account_id',width='12em')

    @metadata(isMain=True,_if='inout=="O"',_if_inout='^.in_out.current', variable_struct=True)
    def th_sections_sendingstatus(self):
        return [dict(code='drafts',caption='!!Drafts',condition="$__is_draft IS TRUE",includeDraft=True),
                dict(code='to_send',caption='!!Ready to send',isDefault=True,condition='$send_date IS NULL AND $error_msg IS NULL'),
                dict(code='sending_error',caption='!!Sending error',condition='$error_msg IS NOT NULL', struct='sending_error'),
                dict(code='sent',caption='!!Sent',includeDraft=False,condition='$send_date IS NOT NULL', struct='sent'),
                dict(code='all',caption='!!All',includeDraft=True)]

    def th_options(self):
        return dict(groupable=dict(width='280px', closable='open'))
    
    
class ViewOutOnly(View):
        
    def th_top_upperbar(self,top):
        top.slotToolbar('5,sections@sendingstatus,*,sections@msg_type',
                        childname='upper',_position='<bar')

    @metadata(isMain=True, variable_struct=True)
    def th_sections_sendingstatus(self):
        return [dict(code='drafts',caption='!!Drafts',condition="$__is_draft IS TRUE",includeDraft=True),
                dict(code='to_send',caption='!!Ready to send',isDefault=True,condition='$send_date IS NULL AND $error_msg IS NULL'),
                dict(code='sending_error',caption='!!Sending error',condition='$error_msg IS NOT NULL', struct='sending_error'),
                dict(code='sent',caption='!!Sent',includeDraft=False,condition='$send_date IS NOT NULL'),
                dict(code='all',caption='!!All',includeDraft=True)]


    @metadata(isMain=True)
    def th_sections_msg_type(self):
        msg_types=self.db.table('email.message_type').query().fetch()
        result = [dict(code='all',caption='All',includeDraft=True)]
        for mt in msg_types:
            result.append(dict(code=mt['code'], caption=mt['description'], condition='$message_type=:m', condition_m=mt['code']))
        return result

    def th_options(self):
        return dict()

    def th_condition(self):
        return dict(condition='$in_out=:io',condition_io='O')



class ViewInOnly(View):
    def th_top_upperbar(self,top):
        pass

    def th_condition(self):
        return dict(condition='$in_out=:io',condition_io='I')

    

class ViewFromMailbox(View):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('to_address',width='7em')
        r.fieldcell('from_address',width='7em')
        r.fieldcell('cc_address',width='7em')
        r.fieldcell('bcc_address',width='7em')
        r.fieldcell('uid',width='7em')
        r.fieldcell('body',width='7em')
        r.fieldcell('body_plain',width='7em')
        r.fieldcell('html',width='7em')
        r.fieldcell('subject',width='7em')
        r.fieldcell('send_date',width='7em')
        r.fieldcell('user_id',width='35em')
        r.fieldcell('account_id',width='35em')

class ViewFromDashboard(View):
    
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('send_date',width='7em',dtype='DH')
        r.fieldcell('to_address',width='12em')
        r.fieldcell('from_address',width='12em')
        r.fieldcell('subject',width='100%')
        r.fieldcell('account_id',hidden=True)
        r.fieldcell('mailbox_id',hidden=True)

    def th_order(self):
        return 'send_date:d'
    
    
class ViewMobile(BaseComponent):
    
    def baseCondition(self):
        return '$dest_user_id=:env_user_id'
    
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('__ins_ts',hidden=True)
        r.fieldcell('send_date',hidden=True)
        r.fieldcell('subject',hidden=True)
        r.fieldcell('abstract',hidden=True)
        r.fieldcell('read',hidden=True)
        r.fieldcell('show_read',hidden=True)
        r.cell('template_row', rowTemplate="""<div>
                                                    <div style='display:flex;align-items:center;justify-content:space-between;padding-top:5px;padding-bottom:5px;'>
                                                        <div style='width:10px;margin-right:10px;'>$show_read</div>
                                                        <div style='width:100%;display: flex;justify-content: space-between;'>
                                                            <div style='font-weight:600'>$subject</div>
                                                            <div style='font-size:.9em'>$send_date</div>
                                                        </div>
                                                    </div>
                                                    <div style='font-size:80%'>$abstract</div>
                                            </div>""", width='100%')

    def th_order(self):
        return '$__ins_ts:d'
        
    def th_condition(self):
        return dict(condition='^messageFilters.condition',
                    condition_type='=messageFilters.type',
                    condition_from_date='=messageFilters.from_date',
                    condition_to_date='=messageFilters.to_date')
    
    @customizable    
    def th_top_readingstate(self, top):
        bar = top.slotToolbar('sections@readingstate,*,filters', _class='mobile_bar', margin_bottom='20px')
        dlg = self.filtersDialog(bar.filters)
        bar.filters.slotButton(_class='google_icon filters', background='#555', height='35px').dataController(
                                    "dlg.show();", dlg=dlg.js_widget)
        return top
    
    def th_sections_readingstate(self):
        return [dict(code='to_read', caption='!![en]Unread', condition="$read IS NOT TRUE"),
                   dict(code='all', caption='!![en]All')]
        

    def filtersDialog(self, pane):
        dlg = pane.dialog(title='!![en]Filter messages', width='320px', height='130px', top='300px', 
                                    datapath='messageFilters', closable=True)
        fb = dlg.mobileFormBuilder(cols=2, border_spacing='4px', padding='5px')
        fb.dbSelect('^.type', table='email.message_type', lbl='!![en]Message type', colspan=2, hasDownArrow=True)
        fb.dateTextBox('^.from_date', lbl='!![en]From date')
        fb.dateTextBox('^.to_date', lbl='!![en]To date')
        dlg.dataController("""SET messageFilters.base_condition=base_condition""",
                           base_condition=self.baseCondition(), _onStart=True)
        dlg.dataController("""var condition_list = [base_condition];
                            if(type){
                                condition_list.push('$message_type=:type');
                            };
                            if(from_date){
                                condition_list.push('$send_date>=:from_date');
                            };
                            if(to_date){
                                condition_list.push('$send_date<=:to_date');
                            };
                            var condition = condition_list.join(" AND ");
                            SET .condition = condition;
                            """, 
                            type='^.type',
                            from_date='^.from_date',
                            to_date='^.to_date',
                            base_condition='^messageFilters.base_condition',
                            _onStart=1)
        return dlg
    
    def th_options(self):
        return dict(widget='dialog', mobileTemplateGrid=True,    
                    configurable=False,roundedEnvelope=True,
                    dialog_fullScreen=True,
                    extendedQuery=False, addrow=False, delrow=False)
        

class Form(BaseComponent):
    py_requires = "gnrcomponents/attachmanager/attachmanager:AttachManager"

    def attemptStruct(self,struct ):
        r = struct.view().rows()
        r.cell('tag',name='Tag', width='7em')
        r.cell('ts',name='Ts')
        r.cell('error',name='Error', width='100%')

    def th_form(self, form):
        bc = form.center.borderContainer(margin='5px')
        top = bc.contentPane(region='top',datapath='.record')
        fb = top.div(margin_right='20px').formbuilder(cols=4,border_spacing='3px',
                                                    fld_width='100%',
                                                    width='100%',
                                                    colswidth='auto')
        fb.field('in_out')
        fb.field('subject', colspan=3)
        fb.field('to_address',colspan=2)
        fb.field('from_address',colspan=2)
        fb.field('cc_address',colspan=2)
        fb.field('bcc_address',colspan=2)
        fb.field('send_date', tag='div')
        fb.field('html',html_label=True)
        fb.field('__is_draft', lbl='!![en]Draft')

        tc = bc.tabContainer(region='center', margin_top='15px')
        tc.contentPane(title='!![en]Body').simpleTextArea(value='^.record.body',editor=True)
        sc = tc.stackContainer(title='!![en]Attachments')
        sc.plainTableHandler(relation='@attachments',pbl_classes=True)
        sc.attachmentGrid(pbl_classes=True)
        tc.dataController("sc.switchPage(in_out=='O'?1:0)",sc=sc.js_widget,in_out='^#FORM.record.in_out')
        tc.contentPane(title='!![en]Body plain', hidden='^.record.body_plain?=!#v').simpleTextArea(value='^.record.body_plain',height='100%')
        errors_pane = tc.contentPane(title='!![en]Errors', region='center', datapath='.record')
        errors_bg = errors_pane.bagGrid(frameCode='sending_attempts',title='Attempts',datapath='#FORM.errors',
                                                            struct=self.attemptStruct,
                                                            storepath='#FORM.record.sending_attempt',
                                                            pbl_classes=True,margin='2px',
                                                            delrow=False,datamode='attr')
        errors_bg.top.bar.replaceSlots('addrow','clearerr,2')
        errors_bg.top.bar.clearerr.slotButton('Clear errors').dataRpc(
                    self.db.table('email.message').clearErrors, pkey='=#FORM.record.id', _onResult='this.form.reload();')

    def th_top_custom(self,top):
        bar = top.bar.replaceSlots('form_delete','send_button,5,form_delete')
        bar.send_button.slotButton('Send message', hidden='^#FORM.record.send_date').dataRpc(
                    self.db.table('email.message').sendMessage, pkey='=#FORM.record.id')

class FormFromDashboard(Form):

    def th_form(self, form):
        pane = form.record
        pane.div('^.body')
    
    def th_options(self):
        return dict(showtoolbar=False)


class FormMobile(BaseComponent):
    py_requires = "gnrcomponents/attachmanager/attachmanager:AttachManager"

    def th_form(self, form):
        bc = form.center.borderContainer(datapath='.record', overflow='auto')
        bc.contentPane(region='center', margin='10px').templateChunk(
                                    table='email.message', record_id='^.id', template='msg_preview')
        
        bc.dataController("bc.widget.setRegionVisible('bottom',read)",bc=bc,read='^#FORM.record.read?=!#v')
        bc.contentPane(region='bottom').div(_class='mobile_button_container', margin_bottom='20px').lightButton(
                        '!!Mark as read', _class='mobile_button').dataRpc(self.db.table('email.message').markAsRead, 
                                                                        pkey='=#FORM.pkey', _onResult="""this.form.dismiss();""")

    def th_options(self):
        return dict(attachmentDrawer=True, modal='navigation')