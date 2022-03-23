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

        
        tbl.column('text_template',name_long='!!Text template')
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


    def impl_SMS(self,action_id=None,**kwargs):
        "Sms"
        pass

    def SMS_pane(self,pane=None,**kwargs):
        frame = pane.framePane()
        bc = frame.center.borderContainer(background='red')

        footer = frame.bottom.slotBar('*,sendSms,5',border_top='1px solid silver',height='22px')
        footer.sendSms.button('Send SMS')


    def impl_email(self,action_id=None,**kwargs):
        "Email"
        pass

    def impl_telegram(self,action_id=None,**kwargs):
        "Telegram"
        pass