# encoding: utf-8
from gnr.core.gnrdecorator import public_method

class Table(object):
    def config_db(self,pkg):
        tbl =  pkg.table('action_type',pkey='id',name_long='!!Action type',name_plural='!!Action types',caption_field='description')
        self.sysFields(tbl,df=True)
        tbl.column('code',size=':10',name_long='Code')
        tbl.column('description',name_long='!!Description')
        tbl.column('extended_description',name_long='!!Extended description')
        tbl.column('restrictions',name_long='!!Restrictions')
        tbl.column('implementor',name_long='!!Implementor')
        tbl.column('default_priority',size='1',name_long='!!Priority',values='L:[!!Low],M:[!!Medium],H:[!!High]')
        tbl.column('default_tag',name_long='!!Default tag')
        tbl.column('show_to_all_tag',dtype='B',name_long='!!Show to all in Tag')
        tbl.column('deadline_days',dtype='I',name_long='!!Deadline days',name_short='DL.Days')
        tbl.column('background_color',name_long='!!Background')
        tbl.column('color',name_long='!!Text color')

        
        tbl.column('text_template',name_long='!!Text template',dtype='X',group='_')
        tbl.column('full_template',dtype='X',group='_',name_long='!!Full template')
        

    @public_method
    def runImplementor(self,action_id=None,implementor=None,**kwargs):
        return getattr(self,f'impl_{implementor}')(action_id,**kwargs)

    def action_implementors(self):
        result = []
        for key in dir(self):
            if key.startswith('impl_'):
                handler = getattr(self,key)
                name = handler.__doc__ or key[5:]
                result.append((key[5:],name,handler))
        return result


    def impl_SMS(self,action_id=None,sms_number=None,sms_content=None,**kwargs):
        "Sms"
        sms_number = sms_number or self._SMS_get_number(action_id)
        sms_content = sms_content or self._SMS_get_content(action_id)
        sms_service_name = self.db.application.getPreference('sms_service',pkg='orgn') or 'sms'
        sms_service = self.db.application.site.getService('sms',sms_service_name)
        result = sms_service.sendsms(destination_number=sms_number,message_content=sms_content)

    def _SMS_get_number(self,action_id=None):
        annotation_tbl = self.db.table('orgn.annotation')
        record_action = annotation_tbl.record(action_id).output('bag')
        fkey,fkey_value = annotation_tbl.recordLinkedEntity(record_action)
        sms_number_path = annotation_tbl.column(fkey).attributes.get('linked_sms_number')
        return record_action[f'@{fkey}.{sms_number_path}']

    def _SMS_get_content(self,action_id=None):
        annotation_tbl = self.db.table('orgn.annotation')
        record_action = annotation_tbl.record(action_id).output('bag')
        template = record_action['@action_type_id.text_template']['compiled']
        return self.db.currentPage.renderTemplate(record_id=action_id,table='orgn.annotation',template=template)


    def SMS_pane(self,pane=None,action_id=None,**kwargs):
        frame = pane.framePane()
        bc = frame.center.borderContainer(datapath='#FORM.impl_sms')
        annotation_tbl = self.db.table('orgn.annotation')
        record_action = annotation_tbl.record(action_id).output('bag')
        sms_number = self._SMS_get_number(action_id)
        fb = bc.contentPane(region='top').formbuilder()
        fb.textbox(value='^.sms_number',lbl='Sms Number',default=sms_number)
        bc.simpleTextArea(value='^.sms_content',region='center')
        template = record_action['@action_type_id.text_template']
        renderedTemplate = self.db.currentPage.renderTemplate(record_id=action_id,table='orgn.annotation',template=template['compiled'])
        bc.data('.sms_content',renderedTemplate)
        footer = frame.bottom.slotBar('*,sendSms,5',border_top='1px solid silver',height='22px')
        footer.sendSms.button('Send SMS').dataRpc(self.runImplementor,
                                                implementor='SMS',
                                                action_id='=#FORM.record.id',
                                                sms_number='=#FORM.impl_sms.sms_number',
                                                sms_content='=#FORM.impl_sms.sms_content')


    def impl_email(self,action_id=None,**kwargs):
        "Email"
        pass

    def impl_telegram(self,action_id=None,**kwargs):
        "Telegram"
        pass