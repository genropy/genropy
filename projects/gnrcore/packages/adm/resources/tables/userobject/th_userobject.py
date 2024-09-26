# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag

class View(BaseComponent):
    def th_hiddencolumns(self):
        return '$data'

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('code',width='10em')
        r.fieldcell('objtype',width='10em')
        r.fieldcell('pkg',width='6em')
        r.fieldcell('tbl',width='20em')
        r.fieldcell('userid',width='6em')
        r.fieldcell('description',width='20em')
        r.fieldcell('authtags',width='6em', name='!![en]Tags')
        r.fieldcell('private',width='3em', tick=True, name='!![en]Priv.')
        r.fieldcell('flags',width='6em')
        r.fieldcell('required_pkg',width='10em')
        r.fieldcell('__mod_ts',name='Local modTS',width='8em')
        r.fieldcell('resource_status',width='20em')

        if self.isDeveloper():
            r.cell('save_as_resource',calculated=True,format_buttonclass='buttonInGrid',
                        format_isbutton='!!Make resource',
                        format_onclick="""PUBLISH save_uo_as_resource = {pkeys:this.widget.getSelectedPkeys().length? this.widget.getSelectedPkeys():[this.widget.rowByIndex($1.rowIndex)['_pkey']]};""",
                        name=' ',width='8em')

    def th_order(self):
        return 'code'

    def th_options(self):
        return dict(virtualStore=False,addrow=False)

    def th_view(self,view):
        view.dataRpc(None,self.db.table('adm.userobject').saveAsResource,
                        subscribe_save_uo_as_resource=True,
                       _if='pkeys',_onResult='FIRE .runQueryDo;',
                        _lockScreen=True)
    
    def th_top_custom(self,top):
        top.slotToolbar('2,sections@types,*,sections@systemuserobject,2',childname='upper',_position='<bar')

    def th_bottom_custom(self,bottom):
        bottom.slotToolbar('2,sections@packages,*')

    def th_sections_packages(self):
        return self.th_distinctSections(table='adm.userobject',field='pkg')

    def th_sections_types(self):
        return self.th_distinctSections(table='adm.userobject',field='objtype')

    def th_sections_systemuserobject(self):
        return [dict(code='standard',caption='Standard',
                    condition="$system_userobject IS NOT TRUE"),
                dict(code='system',caption='System',
                    condition="$system_userobject IS TRUE")]

class View_query(BaseComponent):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('code',width='10em')
        r.fieldcell('userid',width='6em')
        r.fieldcell('description',width='20em')
        r.fieldcell('authtags',width='6em')
        r.fieldcell('private',width='6em')
        r.fieldcell('flags',width='6em')

    def th_options(self):
        return dict(virtualStore=False,addrow=False)

class Form(BaseComponent):

    def th_form(self, form):
        bc = form.center.borderContainer(datapath='.record')
        self.objectParameters(bc.roundedGroup(title='!![en]Object parameters', region='top', height='320px'))
        self.objectResourceForm(bc.stackContainer(region='center', selectedPage='^.objtype', margin='2px'))
        
    def objectResourceForm(self,sc):
        for obj in self.db.table('adm.userobject').query(columns='$objtype',distinct=True).fetch():
            objtype = obj['objtype']
            getattr(self,f'objectResource_{objtype}',self.objectResource_base)(sc.borderContainer(pageName=objtype))

    def objectResource_base(self,bc):
        pass

    def objectResource_query(self,bc):
        pass

    def objectResource_template(self,bc):
        bc.roundedGroup(title='!![en]Template management').templateChunk(template='^#FORM.record.data',
                                       editable=True,
                                       height='100%',
                                       min_height='400px',
                                       table='^#FORM.record.tbl',
                                       selfsubscribe_onChunkEdit='this.form.save();',
                                       padding='5px')

    def objectResource_dash_groupby(self,bc):
        pass

    
        
    def objectParameters(self, pane):
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('code')
        fb.field('description')
        fb.field('objtype')
        fb.field('pkg')
        fb.field('tbl')
        fb.field('userid')
        fb.field('objtype')
        fb.field('notes')
        fb.field('authtags')
        fb.field('private')
        fb.field('quicklist')
        fb.field('flags')
        fb.field('data')

    def th_options(self):
        return dict(copypaste='*')
        

class Form_query(Form):
    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('code')
        fb.field('description')
        fb.field('notes')
        fb.field('authtags')
        fb.field('private')
        fb.field('quicklist')
        fb.field('flags')
        


class View_rpcquery(View_query):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('code',width='8em')
        r.fieldcell('description',width='25em')
        r.fieldcell('userid',width='6em')

class Form_rpcquery(BaseComponent):
    def th_form(self, form):
        bc = form.center.borderContainer()
        fb = bc.contentPane(region='top').formbuilder(cols=2, border_spacing='4px',
                                                    datapath='.record')
        fb.field('code')
        fb.field('description')
        fb.field('notes',colspan=2,width='100%')
        fb.div('^.data.where_as_html',height='80px',width='100%',overflow='auto',
                    colspan=2,_class='fakeTextBox',lbl='Where')
        center = bc.tabContainer(region='center',margin='2px')
        self.tokenManagement(center.borderContainer(title='Tokens'))
        center.contentPane(title='Extended parameters').tree(storepath='#FORM.record.data')


    def tokenManagement(self,bc):
        th = bc.contentPane(region='center').plainTableHandler(relation='@tokens',delrow=True,
                                                                grid_selected_external_url='#FORM.current_external_url',
                                                                    viewResource='ViewFromUserobject')
        bar = th.view.top.bar.replaceSlots('delrow','delrow,addtoken')
        bar.addtoken.slotButton('Add token').dataRpc(self.addRpcQueryToken,
                                        _ask=dict(title='Get token',
                                                    fields=[dict(name='max_usages',tag='numberTextBox',lbl='Max usages'),
                                                            dict(name='expiry',tag='dateTimeTextBox',lbl='Expiry'),
                                                            dict(name='allowed_user',lbl='Allowed user')]),
                                        userobject_id='=#FORM.record.id')

    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px',duplicate=True)
    
    @public_method
    def addRpcQueryToken(self,userobject_id=None,max_usages=None,expiry=None,allowed_user=None):
        self.db.table('sys.external_token').create_token(
            page_path='/sys/rpcquery_token',
            method='execute',

            userobject_id=userobject_id,
            max_usages=max_usages,
            expiry=expiry,
            allowed_user=allowed_user
        )
        self.db.commit()

class ViewCustomColumn(BaseComponent):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('code',width='10em')
        r.fieldcell('userid',width='6em')
        r.fieldcell('description',width='6em')
        r.fieldcell('notes',width='6em')
        r.fieldcell('authtags',width='6em')
        r.fieldcell('private',width='6em')
        
    def th_order(self):
        return 'code'

    def th_query(self):
        return dict(column='objtype', op='contains', val='')

    def th_condition(self):
        return dict(condition='$tbl=:curr_tbl AND $objtype=:ot',condition_ot='formulacolumn',condition_curr_tbl='=current.tbl')

    def th_options(self):
        return dict(virtualStore=False)

class FormCustomColumn(BaseComponent):

    def th_form(self, form):
        pane = form.record.div(margin_left='10px',margin_right='20px',margin_top='10px')
        fb = pane.formbuilder(cols=2, border_spacing='4px',width='100%',fld_width='100%')
        fb.field('code',validate_notnull=True)
        fb.field('description',validate_notnull=True)
        fb.field('notes',colspan=2)
        fb.field('private',html_label=True)
        fb.filteringSelect(value='^.data.dtype',values='B:[!![en]Boolean],T:[!![en]Text],N:[!![en]Numeric],L:[!![en]Integer]',lbl='!!Data type',validate_notnull=True)
        fb.textbox(value='^.data.fieldname',lbl='!!Field',validate_notnull=True)
        fb.textbox(value='^.data.group',lbl='!!Group')
        fb.simpleTextArea(value='^.data.sql_formula',lbl='Sql',colspan=2,width='100%',height='50px')


    @public_method
    def th_onLoading(self,record, newrecord, loadingParameters, recInfo):
        if newrecord:
            record['userid'] = self.user


    def th_options(self):
        return dict(#newTitleTemplate='!!New custom column',titleTemplate='Column:$code-$description',modal=True,
                    default_objtype='formulacolumn',
                    default_tbl='=current.tbl',
                    default_pkg='=current.pkg',dialog_height='210px',dialog_width='500px',
                    duplicate=True)



