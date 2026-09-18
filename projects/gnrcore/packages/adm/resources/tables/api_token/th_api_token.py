# encoding: utf-8

from datetime import datetime, timezone

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method, metadata


class View(BaseComponent):
    css_requires = 'adm'

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('description', width='20em')
        r.fieldcell('group_code', name='!!Group', width='10em')
        r.cell('status', name='!!Status', width='10em',
               rowTemplate=(
                   '<span class="status_dot status_$status"></span>'
                   '<span class="status_label">$status</span>'))
        r.fieldcell('token_hint', name='!!Token', width='8em')
        r.fieldcell('all_tags', name='!!Tags', width='20em')
        r.fieldcell('@created_by.fullname', name='!!Created By', width='12em')
        r.fieldcell('expires_ts', width='12em')
        r.fieldcell('last_used_ts', width='12em')

    def th_top_custom(self, top):
        top.slotToolbar('10,sections@status,*',
                        childname='lifecycle',
                        _position='<bar')

    @metadata(multiButton=True)
    def th_sections_status(self):
        now = datetime.now(timezone.utc)
        return [
            dict(code='to_activate', caption='!!To activate',
                 condition="$token IS NULL"),
            dict(code='active', caption='!!Active',
                 condition="$token IS NOT NULL AND $is_active=:a"
                           " AND ($expires_ts IS NULL OR $expires_ts>=:now)",
                 condition_a=True, condition_now=now),
            dict(code='expired', caption='!!Expired',
                 condition="$expires_ts IS NOT NULL AND $expires_ts<:now",
                 condition_now=now),
            dict(code='inactive', caption='!!Inactive',
                 condition="$is_active=:a", condition_a=False),
            dict(code='all', caption='!!All'),
        ]

    def th_order(self):
        return 'description'

    def th_query(self):
        return dict(column='description', op='contains', val='')

    def th_queryBySample(self):
        return dict(fields=[dict(field='description', lbl='!!Description',
                                 width='16em'),
                            dict(field='group_code', lbl='!!Group',
                                 width='10em'),
                            dict(field='all_tags', lbl='!!Tags',
                                 width='16em'),
                            dict(field='@created_by.fullname',
                                 lbl='!!Created By', width='12em')],
                    cols=4, isDefault=True)


class Form(BaseComponent):
    css_requires = 'adm'

    def th_form(self, form):
        bc = form.center.borderContainer()
        top = bc.contentPane(region='top', datapath='.record')
        fb = top.formlet(cols=2, border_spacing='4px')
        fb.field('description', colspan=2)
        fb.field('group_code', hasDownArrow=True)
        fb.field('expires_ts')
        fb.field('notes', tag='simpleTextArea', height='4ex', colspan=2)

        self._infoBar(top)
        self._activateTokenFlow(top)

        bc.contentPane(region='center').inlineTableHandler(
            relation='@tags', viewResource='ViewFromApiToken',
            pbl_classes=True, margin='2px', addrow=True,
            picker='tag_id', picker_condition='$child_count=0',
            picker_viewResource=True)

    def _infoBar(self, parent):
        """Ambient record metadata + lifecycle action buttons.

        Single horizontal strip below the editable fields: three readonly
        info cells on the left (token hint, activation ts, last used,
        creator) and three mutually-exclusive lifecycle buttons on the
        right (activate / revoke / reactivate). Keeps the form compact
        and groups everything "passive" about the record in one place.

        Hidden expressions on the buttons use the named-param `==` JS
        form (Sourcerer skill "Path Syntax").
        """
        strip = parent.div(datapath='.record',
                           margin='10px', padding='6px 10px',
                           background='#fafafa',
                           border='1px solid #eee', border_radius='4px',
                           font_size='.85em', color='#555',
                           display='flex', align_items='center')
        info = strip.formlet(cols=4, border_spacing='6px', flex='1')
        info.field('token_hint', tag='div')
        info.field('activated_ts', tag='div', format='short')
        info.field('last_used_ts', tag='div', format='short')
        info.field('@created_by.fullname', tag='div', lbl='!!Created By')

        actions = strip.div(margin_left='10px')
        common = dict(pkey='=#FORM.record.id',
                      isnew='^#FORM.controller.is_newrecord',
                      hastoken='^#FORM.record.token',
                      isactive='^#FORM.record.is_active')

        actions.button(
            '!!Activate token', iconClass='iconbox key',
            hidden='==isnew || hastoken',
            action="genro.publish('activateApiToken', {pkey: pkey});",
            **common)

        actions.button(
            '!!Revoke token',
            hidden='==isnew || !hastoken || !isactive',
            action="genro.publish('revokeApiToken', {pkey: pkey});",
            **common)

        actions.button(
            '!!Reactivate token', iconClass='iconbox reload',
            hidden='==isnew || !hastoken || isactive',
            action="genro.publish('reactivateApiToken', {pkey: pkey});",
            **common)

    def _activateTokenFlow(self, parent):
        """RPC driving the lifecycle flows (activate/revoke/reactivate).

        Activate returns the plaintext token ONCE; we show it via
        `genro.dlg.ask`. Revoke/Reactivate just flip is_active; we reload
        the form so the action bar re-renders with the new state.
        """
        parent.dataRpc(self.activateApiToken,
                       subscribe_activateApiToken=True,
                       _lockScreen=True,
                       _msg='!![en]Copy this token now. It is shown only once — '
                            'only the hash is stored.',
                       _onResult="""
                           if(!result){ return; }
                           var token = result;
                           this.form.reload({onReload: function(){
                               var body = kwargs._msg
                                   + '<pre class="api_token_value">'
                                   + token + '</pre>';
                               genro.dlg.ask(_T('!![en]API Token Activated'),
                                   body,
                                   {copy: _T('!![en]Copy to clipboard'),
                                    close: _T('!![en]Close')},
                                   {copy: function(){
                                       genro.textToClipboard(token, _T('!![en]Copied!'));
                                   }},
                                   {closable: true, width: '520px'});
                           }});
                       """)
        parent.dataRpc(self.revokeApiToken,
                       subscribe_revokeApiToken=True,
                       _lockScreen=True,
                       _ask='!![en]Revoke this API token? The hash stays on'
                            ' record so historical calls remain traceable,'
                            ' but the token can no longer authenticate.',
                       _onResult="this.form.reload();")
        parent.dataRpc(self.reactivateApiToken,
                       subscribe_reactivateApiToken=True,
                       _lockScreen=True,
                       _onResult="this.form.reload();")

    @public_method
    def activateApiToken(self, pkey=None, **kwargs):
        token_value = self.db.table('adm.api_token').activate_api_token(
            record_id=pkey)
        if token_value:
            self.db.commit()
        return token_value

    @public_method
    def revokeApiToken(self, pkey=None, **kwargs):
        result = self.db.table('adm.api_token').revoke_api_token(
            record_id=pkey)
        if result:
            self.db.commit()
        return result

    @public_method
    def reactivateApiToken(self, pkey=None, **kwargs):
        result = self.db.table('adm.api_token').reactivate_api_token(
            record_id=pkey)
        if result:
            self.db.commit()
        return result

    def th_options(self):
        return dict(dialog_height='500px', dialog_width='700px', addrow=False)
