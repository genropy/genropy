# encoding: utf-8

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method


class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('description')
        r.fieldcell('auth_tags')
        r.fieldcell('is_active', width='5em')
        r.fieldcell('token_hint', width='8em')
        r.fieldcell('@created_by.fullname', name='!!Created By', width='12em')
        r.fieldcell('expires_ts', width='12em')
        r.fieldcell('last_used_ts', width='12em')

    def th_order(self):
        return 'description'

    def th_query(self):
        return dict(column='description', op='contains', val='')


class Form(BaseComponent):

    def th_form(self, form):
        bc = form.center.borderContainer()
        pane = bc.contentPane(region='top', datapath='.record')
        fb = pane.div(margin='5px').formbuilder(cols=2, border_spacing='4px',
                                                colswidth='20em', fld_width='100%')
        fb.field('description', colspan=2)
        fb.field('auth_tags', colspan=2)
        fb.field('is_active')
        fb.field('expires_ts')
        fb.field('token_hint', readOnly=True)
        fb.field('last_used_ts', readOnly=True)
        fb.field('created_by')
        fb.field('notes', tag='simpleTextArea', height='6ex', colspan=2)
        fb.button('!!Generate Token', fire='#FORM.generateToken',
                  iconClass='iconbox add_row')
        fb.button('!!Revoke', fire='#FORM.revokeToken',
                  iconClass='iconbox delete', hidden='^.is_active?=!#v')
        bc.dataRpc('#FORM.generatedToken', self.th_generateToken,
                   description='=#FORM.record.description',
                   auth_tags='=#FORM.record.auth_tags',
                   expires_ts='=#FORM.record.expires_ts',
                   notes='=#FORM.record.notes',
                   _fired='^#FORM.generateToken',
                   _lockScreen=True,
                   _onResult="""
                       if(result){
                           genro.dlg.alert('!!Token generated. Copy it now — it will not be shown again.\\n\\n' + result, '!!API Token');
                           this.form.reload();
                       }
                   """)
        bc.dataRpc('dummy', self.th_revokeToken,
                   pkey='=#FORM.record.id',
                   _fired='^#FORM.revokeToken',
                   _lockScreen=True,
                   _onResult='this.form.reload();')

    @public_method
    def th_generateToken(self, description=None, auth_tags=None,
                         expires_ts=None, notes=None, **kwargs):
        created_by = self.db.currentEnv.get('user_id')
        record_id, token_value = self.db.table('adm.api_token').create_api_token(
            description=description,
            auth_tags=auth_tags,
            expires_ts=expires_ts,
            notes=notes,
            created_by=created_by
        )
        return token_value

    @public_method
    def th_revokeToken(self, pkey=None, **kwargs):
        record = self.db.table('adm.api_token').record(pkey=pkey).output('dict')
        record['is_active'] = False
        self.db.table('adm.api_token').update(record)
        self.db.commit()

    def th_options(self):
        return dict(dialog_height='500px', dialog_width='700px', addrow=False)
