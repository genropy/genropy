# encoding: utf-8

from gnr.web.gnrbaseclasses import BaseComponent


class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('@user_id.username', name='!![en]User', width='12em')
        r.fieldcell('connector_id', width='22em')
        r.fieldcell('__ins_ts', name='!![en]Signed', width='12em')
        r.fieldcell('expires', width='12em')
        r.fieldcell('revoked', width='6em')

    def th_order(self):
        return '__ins_ts:d'

    def th_query(self):
        return dict(column='@user_id.username', op='contains', val='')

    def th_options(self):
        return dict(addrow=False, delrow=False)


class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=1, border_spacing='4px')
        fb.field('@user_id.username', lbl='!![en]User', readOnly=True)
        fb.field('connector_id', readOnly=True, width='22em')
        fb.field('expires', readOnly=True)
        fb.field('revoked', readOnly=True)
        # the place of the user is free again when no other connector of the user is valid
        fb.button('!![en]Revoke', hidden='^#FORM.record.revoked',
                  action="genro.publish('revokeGenroappConnector',{pkey:pkey});",
                  pkey='=#FORM.record.id')
        pane.dataRpc(self.db.table('adm.user_connector').revokeConnector,
                     subscribe_revokeGenroappConnector=True, _lockScreen=True,
                     _ask='!![en]Revoke this connector? The device login of GenroApp refuses it from now on.',
                     _onResult='this.form.reload();')

    def th_options(self):
        return dict(dialog_height='260px', dialog_width='520px', readOnly=True)
