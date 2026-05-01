# encoding: utf-8

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method


class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('description', width='20em')
        r.fieldcell('group_code', name='!!Group', width='10em')
        r.fieldcell('is_active', name='!!Active', width='5em')
        r.fieldcell('token_hint', name='!!Token', width='8em')
        r.fieldcell('all_tags', name='!!Tags', width='20em')
        r.fieldcell('@created_by.fullname', name='!!Created By', width='12em')
        r.fieldcell('expires_ts', width='12em')
        r.fieldcell('last_used_ts', width='12em')

    def th_bottom_custom(self, bottom):
        bar = bottom.slotToolbar('*,createToken,5')
        bar.createToken.slotButton('!!Create New Token',
                        ask=dict(title='!!New API Token',
                                 fields=[dict(name='description', lbl='!!Token name',
                                              validate_notnull=True,
                                              validate_notnull_error='!!Required')]),
                        action="""genro.publish('generateApiToken',
                                    {description: description})""")

    def th_order(self):
        return 'description'

    def th_query(self):
        return dict(column='description', op='contains', val='')


class Form(BaseComponent):

    def th_form(self, form):
        bc = form.center.borderContainer()
        top = bc.contentPane(region='top', datapath='.record', height='200px')
        fb = top.div(margin='10px').formbuilder(cols=2, border_spacing='4px',
                                                colswidth='20em', fld_width='100%')
        fb.field('description', colspan=2)
        fb.field('group_code', hasDownArrow=True)
        fb.field('is_active')
        fb.field('expires_ts')
        fb.field('token_hint', readOnly=True)
        fb.field('last_used_ts', readOnly=True)
        fb.field('@created_by.fullname', readOnly=True, lbl='!!Created By')
        fb.field('notes', tag='simpleTextArea', height='4ex', colspan=2)
        bc.contentPane(region='center').inlineTableHandler(
            relation='@tags', viewResource='ViewFromApiToken',
            pbl_classes=True, margin='2px', addrow=True,
            picker='tag_id', picker_condition='$child_count=0',
            picker_viewResource=True)
        self._tokenGeneratorDialog(bc)

    def _tokenGeneratorDialog(self, parent):
        """Setup the token generation RPC and result dialog."""
        parent.dataRpc('#FORM.newTokenResult', self.generateApiToken,
                       subscribe_generateApiToken=True,
                       _lockScreen=True,
                       _onResult="""
                           if(result){
                               SET #FORM.newTokenResult = result;
                               genro.publish('showTokenDialog');
                           }
                       """)
        dlg = parent.dialog(title='!!New API Token Created',
                            closable=True, datapath='#FORM.tokenDialog',
                            width='500px',
                            connect_show="""
                                this.setRelativeData('.token',
                                    genro.getData('#FORM.newTokenResult.token'));
                            """)
        pane = dlg.contentPane(padding='15px')
        pane.div('!!Copy this token now. It will not be shown again.',
                 font_weight='bold', margin_bottom='10px', color='#c00')
        pane.div(margin_bottom='10px').textarea(value='^.token',
                 readonly=True, width='100%', height='60px',
                 font_family='monospace', font_size='.85em',
                 lbl='!!Token')
        bar = pane.div(text_align='right')
        bar.button('!!Copy to clipboard',
                   iconClass='iconbox copy',
                   action="""
                       var token = GET .token;
                       genro.textToClipboard(token, 'Copied!');
                   """)
        bar.button('!!Close', action='this.widget.getParentWidget("dialog").hide();',
                   margin_left='10px')
        dlg.dataController("""
            this.widget.show();
        """, subscribe_showTokenDialog=True)

    @public_method
    def generateApiToken(self, description=None, **kwargs):
        created_by = self.db.currentEnv.get('user_id')
        record_id, token_value = self.db.table('adm.api_token').create_api_token(
            description=description or 'New API Token',
            created_by=created_by
        )
        return dict(pkey=record_id, token=token_value)

    def th_options(self):
        return dict(dialog_height='500px', dialog_width='700px', addrow=False)
